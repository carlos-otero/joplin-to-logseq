import os
import time
import re
import sys  # <--- IMPORTANTE: Asegúrate de importar sys
import google.generativeai as genai
from pathlib import Path

# --- FUNCIÓN PARA CARGAR LA CLAVE ---
def load_api_key(filename="api_key.txt"):
    try:
        # Busca el archivo en la misma carpeta que el script
        key_path = Path(__file__).parent / filename
        with open(key_path, "r", encoding="utf-8") as f:
            key = f.read().strip() # Quita espacios y saltos de línea
            if not key:
                print(f"❌ Error: El archivo '{filename}' está vacío.")
                sys.exit(1)
            return key
    except FileNotFoundError:
        print(f"❌ Error Crítico: No encuentro el archivo '{filename}'.")
        print("   -> Crea un archivo 'api_key.txt' y pega tu API Key dentro.")
        sys.exit(1)

# --- CONFIGURACIÓN ---
# 1. Cargamos la API Key desde el archivo externo
API_KEY = load_api_key()

# 2. Carpetas
PAGES_DIR = "logseq-output/pages"

# 3. Modelo (Flash es rápido y barato/gratis)
MODEL_NAME = "gemini-2.0-flash"

# 4. Seguridad: Límite de notas para probar (Pon 0 para procesar TODAS)
TEST_LIMIT = 5  

# Configurar Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def generate_metadata(text_content):
    """
    Envía el texto a Gemini y pide tags y resumen.
    """
    prompt = f"""
    Act as a professional archivist for a Personal Knowledge Management system (Logseq).
    Analyze the following note content.
    
    Task:
    1. Identify 2-4 relevant categories/topics for this note.
    2. Write a 1-sentence summary (max 20 words).
    3. Everything in Spanish from Spain.
    
    Format your response strictly as follows (no markdown, just the text):
    TAGS: [[Topic1]], [[Topic2]], [[Topic3]]
    SUMMARY: The summary text here.
    
    Note Content:
    {text_content[:8000]}  # Limitamos caracteres por si acaso
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

    # Evitar procesar si ya lo hizo la IA (buscamos la marca)
    if "ai-summary::" in content:
        print(f"⏩ Saltando (Ya procesado): {file_path.name}")
        return False

    # Llamar a la IA
    print(f"🧠 Analizando: {file_path.name}...")
    ai_response = generate_metadata(content)
    
    if not ai_response:
        return False

    # Procesar respuesta (Parseo simple)
    tags_line = ""
    summary_line = ""
    
    for line in ai_response.split('\n'):
        if line.startswith("TAGS:"):
            tags_line = line.replace("TAGS:", "tags::").strip()
        elif line.startswith("SUMMARY:"):
            summary_line = line.replace("SUMMARY:", "ai-summary::").strip()

    if not tags_line or not summary_line:
        print("   ❌ Respuesta IA no válida, saltando.")
        return False

    # Inyectar en el FrontMatter (Bloque YAML)
    # Buscamos el segundo '---'
    parts = content.split('---', 2)
    
    if len(parts) >= 3:
        # Existe Frontmatter, lo insertamos al final del bloque
        frontmatter = parts[1]
        body = parts[2]
        
        # Añadimos las nuevas propiedades
        new_frontmatter = frontmatter.rstrip() + f"\n{tags_line}\n{summary_line}\n"
        
        new_content = f"---{new_frontmatter}---{body}"
    else:
        # No existe Frontmatter, lo creamos
        new_content = f"---\n{tags_line}\n{summary_line}\n---\n{content}"

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"   ✅ Etiquetado: {tags_line}")
    return True

def main():
    path = Path(PAGES_DIR)
    if not path.exists():
        print(f"❌ No encuentro la carpeta {PAGES_DIR}")
        return

    files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md']
    print(f"📂 Encontradas {len(files)} notas.")
    
    count = 0
    for file in files:
        # Control de límite de prueba
        if TEST_LIMIT > 0 and count >= TEST_LIMIT:
            print(f"\n🛑 Límite de prueba alcanzado ({TEST_LIMIT}). Cambia TEST_LIMIT = 0 en el script para procesar todo.")
            break

        success = update_note(file)
        
        if success:
            count += 1
            # 🛑 RATE LIMIT: Pausa de seguridad para no saturar la API gratuita (15 peticiones/min aprox)
            time.sleep(4) 

if __name__ == "__main__":
    main()