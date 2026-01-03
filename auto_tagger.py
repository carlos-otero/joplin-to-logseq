import os
import time
import re
import sys
from pathlib import Path

# --- INTENTO DE IMPORTACIÓN ---
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# --- CONFIGURACIÓN ---
PAGES_DIR = "logseq-output/pages"
TEST_LIMIT = 0
OLLAMA_MODEL = "llama3.1"
GEMINI_MODEL = "gemini-2.0-flash"

def load_api_key(filename="api_key.txt"):
    try:
        key_path = Path(__file__).parent / filename
        with open(key_path, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if not key:
                print(f"❌ Error: '{filename}' está vacío.")
                sys.exit(1)
            return key
    except FileNotFoundError:
        print(f"❌ Error: Falta '{filename}' para Gemini.")
        sys.exit(1)

def get_prompt(text_content):
    # Prompt reforzado con EJEMPLO VISUAL para que la IA no se pierda
    return f"""
    You are an archivist for a Logseq system. Analyze the note below.
    
    Task:
    1. Tags: Identify 2-4 topics.
    2. Summary: Write a 1-sentence summary (max 20 words) in Spanish.
    
    CRITICAL OUTPUT FORMAT:
    You must output strictly 2 lines. Do not use Markdown bolding (no **).
    
    Example of valid output:
    TAGS: [[Work]], [[Meeting]], [[Project X]]
    SUMMARY: Notas de la reunión sobre el avance del proyecto X y plazos.
    
    Note Content:
    {text_content[:6000]} 
    """

# --- MOTORES ---
def generate_with_ollama(text):
    if not HAS_OLLAMA: return "MISSING_LIB"
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[
            {'role': 'user', 'content': get_prompt(text)},
        ])
        return response['message']['content']
    except Exception as e:
        print(f"   ⚠️ Error Ollama: {e}")
        return None

def generate_with_gemini(text):
    if not HAS_GEMINI: return "MISSING_LIB"
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(get_prompt(text))
        return response.text
    except Exception as e:
        print(f"   ⚠️ Error Gemini: {e}")
        return None

# --- PARSEO ROBUSTO (REGEX) ---
def parse_ai_response(response_text):
    """
    Intenta extraer TAGS y SUMMARY usando expresiones regulares
    para ser tolerante a errores de formato de la IA (negritas, espacios, etc).
    """
    tags = []
    summary = ""

    # Buscar línea de Tags (acepta TAGS:, **TAGS**:, Tags:, etc.)
    # Captura todo lo que sigue hasta el final de la línea
    tags_match = re.search(r'(?:TAGS|ETIQUETAS)\s*:?\s*(.*)', response_text, re.IGNORECASE)
    if tags_match:
        raw_tags = tags_match.group(1).split(',')
        for t in raw_tags:
            # Limpieza agresiva de basura markdown
            clean_t = t.strip().replace('*', '').replace('`', '')
            if clean_t:
                tags.append(clean_t)

    # Buscar línea de Summary
    summary_match = re.search(r'(?:SUMMARY|RESUMEN)\s*:?\s*(.*)', response_text, re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip().replace('*', '') # Quitar negritas si las puso

    return tags, summary

def update_note(file_path, provider):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "ai-summary:" in content: return "SKIPPED"

    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    if not match: return "NO_FRONTMATTER"

    original_block = match.group(1)
    
    # GENERAR
    if provider == "ollama":
        ai_response = generate_with_ollama(content)
    else:
        ai_response = generate_with_gemini(content)

    if ai_response == "MISSING_LIB": return "MISSING_LIB"
    if not ai_response: return "API_ERROR"

    # PARSEAR
    new_tags, new_summary = parse_ai_response(ai_response)

    # CHECK DE FALLO
    if not new_summary:
        # DEBUG: Si falla, descomenta la siguiente línea para ver qué dijo la IA
        # print(f"\n[DEBUG FAIL] Respuesta IA:\n{ai_response}\n")
        return "BAD_RESPONSE"

    # RECONSTRUIR FRONTMATTER
    new_lines = []
    tags_written = False
    
    for line in original_block.split('\n'):
        if not line.strip(): continue
        
        if line.lower().startswith("tags:"):
            parts = line.split(":", 1)
            existing_val = parts[1].strip()
            combined_tags = set()
            for t in existing_val.split(','):
                t = t.strip()
                if t: combined_tags.add(t)
            for t in new_tags:
                if not t.startswith('[[') and not t.endswith(']]'):
                    combined_tags.add(f"[[{t}]]")
                else:
                    combined_tags.add(t)
            
            final_tags_str = ", ".join(sorted(list(combined_tags)))
            new_lines.append(f"tags: {final_tags_str}")
            tags_written = True
        elif line.lower().startswith("ai-summary:"):
            continue 
        else:
            new_lines.append(line)

    if not tags_written and new_tags:
        clean_new_tags = []
        for t in new_tags:
             if not t.startswith('[[') and not t.endswith(']]'):
                    clean_new_tags.append(f"[[{t}]]")
             else:
                    clean_new_tags.append(t)
        new_lines.append(f"tags: {', '.join(clean_new_tags)}")

    new_lines.append(f"ai-summary: {new_summary}")
    new_frontmatter = "---\n" + "\n".join(new_lines) + "\n---\n"
    new_content = content.replace(match.group(0), new_frontmatter)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return "SUCCESS"

def draw_progress_bar(current, total, bar_length=20):
    percent = float(current) * 100 / total
    arrow = '█' * int(percent/100 * bar_length - 1)
    spaces = '░' * (bar_length - len(arrow))
    return f"[{arrow}{spaces}] {int(percent)}%"

def main():
    print("🤖 AUTO TAGGER V3.1 (Robust Parser)")
    print("-----------------------------------")
    print("1. Ollama (Local)")
    print("2. Gemini (Cloud)")
    choice = input("\nOpción [1/2]: ").strip()
    
    provider = "ollama"
    if choice == "2":
        provider = "gemini"
        if not HAS_GEMINI:
            print("❌ Falta librería google-generativeai.")
            return
        genai.configure(api_key=load_api_key())
    else:
        if not HAS_OLLAMA:
            print("❌ Falta librería ollama.")
            return

    path = Path(PAGES_DIR)
    if not path.exists():
        print(f"❌ No existe {PAGES_DIR}")
        return

    all_files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md']
    total_files = len(all_files)
    limit = TEST_LIMIT if TEST_LIMIT > 0 else total_files
    files_to_process = all_files[:limit]
    
    print(f"\n📂 Procesando {len(files_to_process)} notas...")
    print("-" * 60)
    
    stats = {"ok":0, "skip":0, "err":0}

    for i, file in enumerate(files_to_process, 1):
        bar = draw_progress_bar(i, len(files_to_process))
        print(f"\n{bar} | {i}/{len(files_to_process)} | {file.name}")

        status = update_note(file, provider)
        
        if status == "SUCCESS":
            print(f"   ✅ Listo")
            stats["ok"] += 1
            if provider == "gemini": time.sleep(3)
        elif status == "SKIPPED":
            print(f"   ⏩ Saltado")
            stats["skip"] += 1
        else:
            print(f"   ❌ Fallo: {status}")
            stats["err"] += 1

    print("\n" + "=" * 60)
    print(f"🏁 HECHO: ✅{stats['ok']}  ⏩{stats['skip']}  ❌{stats['err']}")

if __name__ == "__main__":
    main()