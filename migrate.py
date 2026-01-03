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

# Tags automáticos (Se fusionarán con los existentes)
# Nota: Logseq prefiere [[WikiLinks]] en los tags
AUTO_TAGS = ["[[Joplin]]", "[[Por Procesar]]"]

# Metadatos a ELIMINAR COMPLETAMENTE
METADATA_BLACKLIST = [
    "latitude", "longitude", "altitude", 
    "author", "source", "source_url", 
    "is_todo", "todo_due", "todo_completed", 
    "id", "parent_id", "type_"
]

def sanitize_name(name):
    """Limpia nombres de archivo y carpetas."""
    try:
        name = html.unescape(name)
    except:
        pass
    clean_name = name.strip().lstrip(':. -_').rstrip()
    if not clean_name:
        return "Sin_Titulo_" + str(int(datetime.now().timestamp()))
    return clean_name

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
    
    properties = {}
    tags_set = set(AUTO_TAGS) # Iniciamos con los tags automáticos
    original_title_clean = sanitize_name(Path(original_filename).stem)
    
    # Propiedades obligatorias iniciales
    properties['title'] = hierarchy_title
    properties['alias'] = original_title_clean
    
    if match:
        original_block = match.group(1)
        for line in original_block.split('\n'):
            if not line.strip() or ":" not in line: continue
            
            key_raw, val = line.split(':', 1)
            key = key_raw.strip()
            key_lower = key.lower() # Normalizamos para detectar duplicados (Tags vs tags)
            val = val.strip()

            if key_lower in METADATA_BLACKLIST: continue
            
            # --- PROCESAMIENTO DE TAGS (Case Insensitive) ---
            if key_lower == "tags":
                # Joplin separa por comas
                current_tags = [t.strip() for t in val.split(',')]
                for t in current_tags:
                    if not t: continue
                    # Aseguramos formato [[Tag]]
                    if not t.startswith('[[') and not t.endswith(']]'):
                        tags_set.add(f"[[{t}]]")
                    else:
                        tags_set.add(t)
                continue # Saltamos para no añadirlo a 'properties' y evitar duplicado

            # --- FECHAS ---
            if key_lower == "created_time" or key_lower == "created":
                ts, dl = parse_joplin_date(val)
                if ts:
                    properties['created-at'] = ts
                    properties['date'] = dl
                continue
            
            if key_lower == "updated_time" or key_lower == "updated":
                ts, _ = parse_joplin_date(val)
                if ts: properties['updated-at'] = ts
                continue

            # --- ALIAS / TITULO ---
            if key_lower == "title":
                val = val.strip('"').strip("'")
                val_clean = sanitize_name(val)
                if val_clean and val_clean != original_title_clean:
                    properties['alias'] = val_clean
                continue
            
            # --- CUALQUIER OTRA PROPIEDAD (ai-summary, etc) ---
            # Guardamos usando la clave original (ej: ai-summary)
            properties[key] = val

    # --- CONSTRUCCIÓN DEL NUEVO FRONTMATTER (Sin doble ::) ---
    new_block = "---\n"
    
    # 1. Title
    new_block += f"title: {properties['title']}\n"
    
    # 2. Tags (Fusionados)
    if tags_set:
        sorted_tags = sorted(list(tags_set))
        new_block += f"tags: {', '.join(sorted_tags)}\n"
    
    # 3. Alias
    if 'alias' in properties:
        new_block += f"alias: {properties['alias']}\n"
        
    # 4. Fechas
    if 'date' in properties: new_block += f"date: {properties['date']}\n"
    if 'created-at' in properties: new_block += f"created-at: {properties['created-at']}\n"
    if 'updated-at' in properties: new_block += f"updated-at: {properties['updated-at']}\n"

    # 5. Otras propiedades preservadas
    # Lista de claves que ya hemos escrito manualmente arriba para no repetir
    written_keys_lower = ['title', 'tags', 'alias', 'date', 'created-at', 'updated-at', 'created_time', 'updated_time', 'created', 'updated']
    
    for k, v in properties.items():
        if k.lower() not in written_keys_lower:
            # Aquí usamos solo un ':' como pediste
            new_block += f"{k}: {v}\n"

    new_block += "---\n"
    
    if match:
        return content.replace(match.group(0), new_block)
    else:
        return new_block + content

def clean_and_convert_content(content):
    # 1. Adjuntos
    content = re.sub(r'\((?:(?:\.|)\./)*_resources/', '(../assets/', content)
    
    # 2. Limpieza HTML
    content = re.sub(r'&nbsp;?', ' ', content, flags=re.IGNORECASE)
    content = re.sub(r'&tbsp;?', ' ', content, flags=re.IGNORECASE)
    content = re.sub(r'<br class="jop-noMdConv">', '', content)
    content = re.sub(r'<br>', '\n', content)
    
    # 3. Enlaces Internos
    def link_replacer(match):
        text = match.group(1)
        path = match.group(2)
        if "_resources" in path or "http" in path or "assets" in path:
            return match.group(0)
        filename = sanitize_name(Path(path).stem)
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
    content = f"---\ntitle: Índice de Migración Joplin\ndate: [[{datetime.now().strftime('%Y-%m-%d')}]]\n---\n"
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

    print(f"🚀 Iniciando Migración v3.5 (YAML Estándar + Fix Duplicados)")
    
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
                    
                    # Sanitización
                    rel_path = original_file_path.relative_to(src_path)
                    clean_parts = [sanitize_name(p) for p in rel_path.parent.parts]
                    
                    raw_stem = file[:-3]
                    if file.endswith("..md"): raw_stem = file[:-4]
                    file_stem = sanitize_name(raw_stem)
                    
                    if not file_stem: file_stem = "Sin_Nombre_" + str(int(datetime.now().timestamp()))

                    if clean_parts:
                        filename_structure = ".".join(clean_parts) + "." + file_stem + ".md"
                        hierarchy_title = "/".join(clean_parts) + "/" + file_stem
                    else:
                        filename_structure = file_stem + ".md"
                        hierarchy_title = file_stem
                    
                    unique_name = get_unique_filename(pages_dir, filename_structure)
                    
                    # Procesamiento
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    content = process_frontmatter(content, file, hierarchy_title)
                    content = clean_and_convert_content(content)

                    with open(pages_dir / unique_name, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    migrated_filenames.append(unique_name)
                    
                except Exception as e:
                    print(f"❌ Error en: {file} -> {e}")

    if migrated_filenames:
        generate_index_file(pages_dir, migrated_filenames)

    print(f"🏁 TERMINADO en {datetime.now() - start_time}")
    print(f"✅ Notas migradas: {len(migrated_filenames)}")

if __name__ == "__main__":
    main()