import os
import re
import sys
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
PAGES_DIR = "logseq-output/pages"
INDEX_FILENAME = "000_Indice_Migracion.md"

# 1. Regex para DETECTAR duplicados iniciales (Fase de fusión)
DUPLICATE_PATTERN = re.compile(r'([-_ ]\d+|_+|\.txt[._]?|\(\d+\))+$')

# 2. Regex para LIMPIAR nombres (Fase 3 - Batería de Limpieza)

# A. Fechas tipo ISO (Joplin estándar): -2019-08-30T12_27_09Z
ISO_TIMESTAMP_PATTERN = re.compile(r'-\d{4}-\d{2}-\d{2}T\d{2}[_:]\d{2}[_:]\d{2}Z')

# B. Fechas con espacios (Tu caso específico): - 2015-07-01 16 57 51 -
# Detecta " - YYYY-MM-DD HH MM SS -"
SPACED_TIMESTAMP_PATTERN = re.compile(r' - \d{4}-\d{2}-\d{2} \d{2} \d{2} \d{2}( -)?')

# C. Sufijos basura del final (-1, -2, _, -)
SUFFIX_CLEAN_PATTERN = re.compile(r'([-_ ]\d+|_+|-)+$')

# D. Extensión .txt incrustada al final del nombre (antes del .md)
TXT_EXTENSION_PATTERN = re.compile(r'\.txt$')

def parse_frontmatter(content):
    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    meta = {'tags': set(), 'created-at': 0, 'title': '', 'date': ''}
    body = content
    
    if match:
        yaml_block = match.group(1)
        body = content.replace(match.group(0), "")
        
        for line in yaml_block.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip().lower()
                val = val.strip()
                
                if key == 'created-at':
                    try: meta['created-at'] = int(val)
                    except: pass
                elif key == 'date':
                    meta['date'] = val
                elif key == 'title':
                    meta['title'] = val
                elif key == 'tags':
                    tags = [t.strip() for t in val.split(',')]
                    meta['tags'].update(tags)
                    
    return meta, body.strip()

def find_true_master(filename, all_filenames_set):
    current_name = Path(filename).stem
    while True:
        clean_name = DUPLICATE_PATTERN.sub('', current_name).strip()
        if clean_name == current_name:
            return current_name
        if (clean_name + ".md") in all_filenames_set:
            current_name = clean_name
        else:
            return current_name

def merge_notes(files, force_master_path=None):
    file_data = []
    for f in files:
        if not f.exists(): continue
        with open(f, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read()
            meta, body = parse_frontmatter(content)
            file_data.append({'path': f, 'meta': meta, 'body': body})

    if not file_data: return

    file_data.sort(key=lambda x: x['meta']['created-at'] if x['meta']['created-at'] > 0 else float('inf'))
    
    content_master = file_data[0]
    others = file_data[1:]
    
    if force_master_path:
        final_path = force_master_path
    else:
        final_path = content_master['path']

    print(f"   ⭐ Fusionando en: {final_path.name}")

    for item in others:
        content_master['meta']['tags'].update(item['meta']['tags'])

    final_body = content_master['body']
    for item in others:
        other_body = item['body']
        if not other_body: continue
        
        norm_final = re.sub(r'\s+', '', final_body)
        norm_other = re.sub(r'\s+', '', other_body)
        
        if norm_other in norm_final:
            print(f"     🗑️  Contenido duplicado ignorado de: {item['path'].name}")
            continue
            
        print(f"     ➕ Añadiendo contenido único de: {item['path'].name}")
        final_body += f"\n\n--- \n### 📎 Contenido extra de {item['path'].name}:\n{other_body}"

    sorted_tags = sorted(list(content_master['meta']['tags']))
    tags_line = f"tags: {', '.join(sorted_tags)}"
    
    new_yaml = "---\n"
    new_yaml += f"title: {content_master['meta']['title']}\n"
    new_yaml += f"{tags_line}\n"
    if content_master['meta']['date']: new_yaml += f"date: {content_master['meta']['date']}\n"
    if content_master['meta']['created-at']: new_yaml += f"created-at: {content_master['meta']['created-at']}\n"
    new_yaml += f"alias: {final_path.stem}\n" 
    new_yaml += "---\n"
    
    full_content = new_yaml + final_body

    with open(final_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    for item in file_data:
        if item['path'].resolve() != final_path.resolve():
            try: 
                os.remove(item['path'])
                print(f"     ❌ Borrado archivo redundante: {item['path'].name}")
            except OSError as e: 
                print(f"     ⚠️ Error borrando: {e}")

def clean_filenames_phase(path):
    print("\n" + "="*40)
    print("🧹 FASE 3: LIMPIEZA PROFUNDA DE NOMBRES")
    print("="*40)
    
    files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md']
    processed_count = 0
    
    for f in files:
        if not f.exists(): continue
        
        original_stem = f.stem
        new_stem = original_stem
        
        # --- BATERÍA DE LIMPIEZA ---
        
        # 1. Eliminar el patrón específico "Notas.Nota"
        # Ej: Carlos Otero.Notas.Nota - 2015... -> Carlos Otero.
        if ".Notas.Nota" in new_stem:
             new_stem = new_stem.replace(".Notas.Nota", "")

        # 2. Eliminar el patrón de carpeta "Notas" genérica
        # Ej: Carlos Otero.Notas.Concepto -> Carlos Otero.Concepto
        if ".Notas." in new_stem:
            new_stem = new_stem.replace(".Notas.", ".")

        # 3. Eliminar extensión .txt incrustada
        # Ej: Archivo.txt.md -> Archivo.md
        new_stem = TXT_EXTENSION_PATTERN.sub('', new_stem)

        # 4. Eliminar Fechas con espacios
        # Ej: - 2015-07-01 16 57 51 -
        new_stem = SPACED_TIMESTAMP_PATTERN.sub('.', new_stem)

        # 5. Eliminar Fechas ISO
        # Ej: -2019-08-30T12_27_09Z
        new_stem = ISO_TIMESTAMP_PATTERN.sub('', new_stem)
        
        # 6. Eliminar Sufijos numéricos residuales (-1, _1)
        new_stem = SUFFIX_CLEAN_PATTERN.sub('', new_stem)
        
        # 7. Limpieza final de puntos dobles o espacios
        new_stem = new_stem.replace("..", ".").strip(" .-_")
        
        # ---------------------------
        
        if new_stem != original_stem and new_stem: # Ensure we didn't delete the whole name
            new_path = f.parent / (new_stem + ".md")
            
            if new_path.exists():
                print(f"\n⚠️  COLISIÓN: '{f.name}' -> '{new_path.name}' (Ya existe).")
                print(f"   🔧 Fusionando...")
                merge_notes([new_path, f], force_master_path=new_path)
                processed_count += 1
            else:
                try:
                    f.rename(new_path)
                    print(f"✨ Limpiado: '{f.name}'\n            -> '{new_path.name}'")
                    processed_count += 1
                except OSError as e:
                    print(f"❌ Error renombrando {f.name}: {e}")

    print(f"\n🔹 Archivos procesados: {processed_count}")

def regenerate_index(path):
    print("\n" + "="*40)
    print("🗺️  FASE 4: REGENERANDO ÍNDICE MAESTRO")
    print("="*40)
    
    files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md' and f.name != INDEX_FILENAME]
    files.sort(key=lambda x: x.name)
    
    content = f"---\ntitle: Índice de Migración (Consolidado)\ndate: [[{datetime.now().strftime('%Y-%m-%d')}]]\n---\n"
    content += "### 🚀 Resumen Post-Limpieza\n"
    content += f"Actualizado el: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += f"Total notas consolidadas: {len(files)}\n\n"
    content += "### 📂 Notas Activas\n"
    
    for f in files:
        content += f"- [[{f.stem}]]\n"
        
    with open(path / INDEX_FILENAME, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Índice actualizado: {INDEX_FILENAME} ({len(files)} entradas)")

def main():
    path = Path(PAGES_DIR)
    if not path.exists():
        print(f"❌ Error: No encuentro {PAGES_DIR}")
        return

    # FASE 1 & 2
    all_files = [f for f in path.iterdir() if f.is_file() and f.suffix == '.md']
    all_filenames_set = set(f.name for f in all_files)
    
    print(f"🔍 FASE 1: Análisis inicial de {len(all_files)} archivos...")
    
    groups = {}
    for f in all_files:
        true_master_name = find_true_master(f.name, all_filenames_set)
        if true_master_name not in groups:
            groups[true_master_name] = []
        groups[true_master_name].append(f)
        
    for master_name, file_list in groups.items():
        if len(file_list) > 1:
            merge_notes(file_list)
            
    # FASE 3
    clean_filenames_phase(path)
    
    # FASE 4
    regenerate_index(path)

    print("\n" + "="*40)
    print(f"🏁 PROCESO TERMINADO")
    print("="*40)

if __name__ == "__main__":
    main()