import os
import shutil
import re
import sys
import html
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
SOURCE_DIR = "joplin-input"
OUTPUT_DIR = "logseq-output"
JOPLIN_RESOURCES = "_resources"
LOGSEQ_ASSETS = "assets"
LOGSEQ_PAGES = "pages"

# Tags automáticos para gestión de la migración
AUTO_TAGS = "[[Joplin]], [[Por Procesar]]"

# Metadatos a ELIMINAR
METADATA_BLACKLIST = [
    "latitude", "longitude", "altitude", 
    "author", "source", "source_url", 
    "is_todo", "todo_due", "todo_completed", 
    "id", "parent_id", "type_"
]

def parse_joplin_date(date_str):
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt = datetime.fromisoformat(str(date_str).strip())
        except ValueError:
            return None, None
    
    timestamp = int(dt.timestamp() * 1000)
    date_link = f"[[{dt.strftime('%Y-%m-%d')}]]"
    return timestamp, date_link

def process_frontmatter(content, original_filename, hierarchy_title):
    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    new_properties = {}
    existing_lines = []
    original_title_clean = Path(original_filename).stem
    
    if match:
        original_block = match.group(1)
        for line in original_block.split('\n'):
            if not line.strip() or ":" not in line: continue
            
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()

            if key in METADATA_BLACKLIST: continue
            
            if key == "created_time":
                ts, dl = parse_joplin_date(val)
                if ts:
                    new_properties['created-at'] = ts
                    new_properties['date'] = dl
                continue
            
            if key == "updated_time":
                ts, _ = parse_joplin_date(val)
                if ts: new_properties['updated-at'] = ts
                continue

            if key == "title":
                val = val.strip('"').strip("'")
                if val and val != original_title_clean:
                    new_properties['alias'] = val
                continue
                
            if key == "tags":
                # Mantenemos los tags originales de Joplin
                existing_lines.append(line.replace("tags:", "tags::"))
            else:
                existing_lines.append(line)
    
    # --- CONSTRUCCIÓN DEL NUEVO FRONTMATTER ---
    new_block = "---\n"
    new_block += f"title:: {hierarchy_title}\n"
    
    # INYECCIÓN DE TAGS DE MIGRACIÓN (Aquí está la magia)
    # Logseq permite múltiples líneas 'tags::', las fusionará.
    new_block += f"tags:: {AUTO_TAGS}\n"
    
    if 'alias' in new_properties:
        new_block += f"alias:: {new_properties['alias']}\n"
    else:
        new_block += f"alias:: {original_title_clean}\n"

    if 'date' in new_properties: new_block += f"date:: {new_properties['date']}\n"
    if 'created-at' in new_properties: new_block += f"created-at:: {new_properties['created-at']}\n"
    if 'updated-at' in new_properties: new_block += f"updated-at:: {new_properties['updated-at']}\n"

    for line in existing_lines:
        new_block += f"{line}\n"
        
    new_block += "---\n"
    
    if match:
        return content.replace(match.group(0), new_block)
    else:
        return new_block + content

def clean_and_convert_content(content):
    # 1. Adjuntos (Deep folder fix)
    content = re.sub(r'\((?:(?:\.|)\./)*_resources/', '(../assets/', content)
    
    # 2. Limpieza de Entidades HTML (&nbsp;, &tbsp;)
    content = re.sub(r'&nbsp;?', ' ', content, flags=re.IGNORECASE)
    content = re.sub(r'&tbsp;?', ' ', content, flags=re.IGNORECASE)
    
    # 3. Limpieza de etiquetas basura
    content = re.sub(r'<br class="jop-noMdConv">', '', content)
    content = re.sub(r'<br>', '\n', content)
    
    # 4. Arreglo de Enlaces Internos [Texto](Nota.md) -> [[Nota]]
    def link_replacer(match):
        text = match.group(1)
        path = match.group(2)
        if "_resources" in path or "http" in path or "assets" in path:
            return match.group(0)
        
        filename = Path(path).stem
        return f"[[{filename}]]"

    content = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', link_replacer, content)

    return content

def get_unique_filename(directory, filename):
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while (directory / new_filename).exists():
        new_filename = f"{name}_{counter}{ext}"
        counter += 1
    return new_filename

def generate_index_file(pages_dir, migrated_files):
    index_name = "000_Indice_Migracion.md"
    content = f"---\ntitle:: Índice de Migración Joplin\ndate:: [[{datetime.now().strftime('%Y-%m-%d')}]]\n---\n"
    content += "### 🚀 Resumen de Importación\n"
    content += f"Importado el: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += f"Total notas: {len(migrated_files)}\n\n"
    content += "### 📂 Notas Importadas\n"
    migrated_files.sort()
    for filename in migrated_files:
        link_name = Path(filename).stem
        content += f"- [[{link_name}]]\n"
    with open(pages_dir / index_name, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"🗺️  Índice maestro creado: {index_name}")

def main():
    start_time = datetime.now()
    base_path = Path.cwd()
    src_path = base_path / SOURCE_DIR
    out_path = base_path / OUTPUT_DIR
    
    if not src_path.exists():
        print(f"❌ ERROR: No encuentro la carpeta '{SOURCE_DIR}'")
        sys.exit(1)

    if out_path.exists():
        shutil.rmtree(out_path)
    
    (out_path / LOGSEQ_ASSETS).mkdir(parents=True, exist_ok=True)
    (out_path / LOGSEQ_PAGES).mkdir(parents=True, exist_ok=True)

    print(f"🚀 Iniciando Migración v3.2 (Tags + Limpieza + Jerarquías)")
    
    # PHASE 1: ASSETS
    src_resources = src_path / JOPLIN_RESOURCES
    dest_assets = out_path / LOGSEQ_ASSETS
    if src_resources.exists():
        files = [f for f in src_resources.iterdir() if f.is_file()]
        for item in files:
            shutil.copy2(item, dest_assets / item.name)
        print(f"📦 Assets copiados: {len(files)}")

    # PHASE 2: NOTES
    pages_dir = out_path / LOGSEQ_PAGES
    migrated_filenames = []
    
    for root, dirs, files in os.walk(src_path):
        if JOPLIN_RESOURCES in dirs: dirs.remove(JOPLIN_RESOURCES)
        
        for file in files:
            if file.endswith(".md"):
                try:
                    original_file_path = Path(root) / file
                    
                    # Jerarquía
                    rel_path = original_file_path.relative_to(src_path)
                    parts = list(rel_path.parent.parts)
                    file_stem = file[:-3]
                    if file.endswith("..md"): file_stem = file[:-4]

                    if parts:
                        filename_structure = ".".join(parts) + "." + file_stem + ".md"
                        hierarchy_title = "/".join(parts) + "/" + file_stem
                    else:
                        filename_structure = file_stem + ".md"
                        hierarchy_title = file_stem
                    
                    unique_name = get_unique_filename(pages_dir, filename_structure)
                    
                    # Lectura y Transformación
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    content = process_frontmatter(content, file, hierarchy_title)
                    content = clean_and_convert_content(content)

                    # Escritura
                    with open(pages_dir / unique_name, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    migrated_filenames.append(unique_name)
                    
                except Exception as e:
                    print(f"❌ Error en: {file} -> {e}")

    # PHASE 3: INDEX
    if migrated_filenames:
        generate_index_file(pages_dir, migrated_filenames)

    print(f"🏁 TERMINADO en {datetime.now() - start_time}")
    print(f"✅ Notas migradas: {len(migrated_filenames)}")

if __name__ == "__main__":
    main()