import os
import time
import re
import sys
import google.generativeai as genai
from pathlib import Path

# --- FUNCIÓN PARA CARGAR LA CLAVE ---
def load_api_key(filename="api_key.txt"):
    try:
        key_path = Path(__file__).parent / filename
        with open(key_path, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if not key:
                print(f"❌ Error: El archivo '{filename}' está vacío.")
                sys.exit(1)
            return key
    except FileNotFoundError:
        print(f"❌ Error Crítico: No encuentro el archivo '{filename}'.")
        print("   -> Crea un archivo 'api_key.txt' y pega tu API Key dentro.")
        sys.exit(1)

# --- CONFIGURACIÓN ---
API_KEY = load_api_key()
PAGES_DIR = "logseq-output/pages"
MODEL_NAME = "gemini-2.0-flash"
TEST_LIMIT = 3  # 0 = Procesar TODAS las notas

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def generate_metadata(text_content):
    """
    Envía el texto a Gemini y pide tags y resumen.
    """
    prompt = f"""
    Actúa como un archivista profesional para un sistema Logseq.
    Analiza la siguiente nota.
    
    Tarea:
    1. Identifica 2-4 categorías/temas relevantes (Tags).
    2. Escribe un resumen de 1 frase (máx 20 palabras) en Español de España.
    
    Formato de respuesta ESTRICTO (Solo texto plano):
    TAGS: [[Topic1]], [[Topic2]]
    SUMMARY: Texto del resumen aquí.
    
    Contenido de la nota:
    {text_content[:8000]}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Error de API: {e}")
        return None

def update_note(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Verificar si ya tiene resumen IA para no gastar tokens
    if "ai-summary:" in content:
        print(f"⏩ Saltando (Ya procesado): {file_path.name}")
        return False

    # 2. Extraer Frontmatter existente
    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    if not match:
        print(f"⚠️ Saltando (Sin Frontmatter): {file_path.name}")
        return False

    original_block = match.group(1)
    
    # 3. Llamar a la IA
    print(f"🧠 Analizando: {file_path.name}...")
    ai_response = generate_metadata(content)
    if not ai_response: return False

    # 4. Parsear respuesta de la IA
    new_tags = []
    new_summary = ""
    
    for line in ai_response.split('\n'):
        if line.startswith("TAGS:"):
            # Extraer tags y limpiar
            raw_tags = line.replace("TAGS:", "").strip().split(',')
            for t in raw_tags:
                t = t.strip()
                if t: new_tags.append(t)
        elif line.startswith("SUMMARY:"):
            new_summary = line.replace("SUMMARY:", "").strip()

    if not new_summary:
        print("   ❌ Respuesta IA incompleta.")
        return False

    # 5. Reconstruir el Frontmatter Fusionando Tags
    new_lines = []
    tags_written = False
    
    for line in original_block.split('\n'):
        if not line.strip(): continue
        
        # Detectar línea de tags existente (tags: ...)
        if line.lower().startswith("tags:"):
            parts = line.split(":", 1)
            existing_val = parts[1].strip()
            
            # Crear set para evitar duplicados
            combined_tags = set()
            
            # Añadir existentes
            for t in existing_val.split(','):
                t = t.strip()
                if t: combined_tags.add(t)
            
            # Añadir nuevos de la IA
            for t in new_tags:
                # Asegurar formato [[Tag]]
                if not t.startswith('[[') and not t.endswith(']]'):
                    combined_tags.add(f"[[{t}]]")
                else:
                    combined_tags.add(t)
            
            # Convertir a lista ordenada y escribir
            final_tags_str = ", ".join(sorted(list(combined_tags)))
            new_lines.append(f"tags: {final_tags_str}")
            tags_written = True
        
        # Evitar re-escribir ai-summary si ya existiera (por seguridad)
        elif line.lower().startswith("ai-summary:"):
            continue 
            
        else:
            new_lines.append(line)

    # Si no existía línea de tags, la creamos ahora
    if not tags_written and new_tags:
        clean_new_tags = []
        for t in new_tags:
             if not t.startswith('[[') and not t.endswith(']]'):
                    clean_new_tags.append(f"[[{t}]]")
             else:
                    clean_new_tags.append(t)
        new_lines.append(f"tags: {', '.join(clean_new_tags)}")

    # Añadimos el resumen al final del bloque
    new_lines.append(f"ai-summary: {new_summary}")

    # 6. Escribir archivo
    new_frontmatter = "---\n" + "\n".join(new_lines) + "\n---\n"
    new_content = content.replace(match.group(0), new_frontmatter)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"   ✅ Actualizado (Tags fusionados + Resumen)")
    return True

def main():
    path = Path(PAGES_DIR)
    if not path.exists():
        print(f"❌ No encuentro la carpeta {PAGES_DIR}")
        return

    files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md']
    print(f"📂 Encontradas {len(files)} notas para procesar con IA.")
    
    count = 0
    for file in files:
        if TEST_LIMIT > 0 and count >= TEST_LIMIT:
            print(f"🛑 Límite de prueba alcanzado ({TEST_LIMIT}).")
            break

        success = update_note(file)
        
        if success:
            count += 1
            time.sleep(4) # Rate limit preventivo

if __name__ == "__main__":
    main()