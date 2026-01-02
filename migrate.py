import os
import shutil
import re
import sys
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
SOURCE_DIR = "joplin-input"
OUTPUT_DIR = "logseq-output"
JOPLIN_RESOURCES = "_resources"
LOGSEQ_ASSETS = "assets"
LOGSEQ_PAGES = "pages"

# Metadata to REMOVE (cleanup)
METADATA_BLACKLIST = [
    "latitude", "longitude", "altitude", 
    "author", "source", "source_url", 
    "is_todo", "todo_due", "todo_completed", 
    "id", "parent_id", "created_time", "updated_time", 
    "type_", "title" 
]

def clean_frontmatter(content):
    """
    Parses the YAML block (between ---) and removes unwanted lines.
    Converts Joplin 'tags:' to Logseq 'tags::'.
    """
    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    if not match:
        return content

    original_block = match.group(1)
    new_lines = []
    
    for line in original_block.split('\n'):
        if not line.strip():
            continue
        key = line.split(':')[0].strip()
        if key in METADATA_BLACKLIST:
            continue
        if key == "tags":
            line = line.replace("tags:", "tags::")
        new_lines.append(line)

    if not new_lines:
        return re.sub(yaml_pattern, "", content)
    
    new_block = "---\n" + "\n".join(new_lines) + "\n---\n"
    return content.replace(match.group(0), new_block)

def get_unique_filename(directory, filename):
    """
    Checks if a file exists in the directory. If it does, adds a counter
    to the filename (e.g., file_1.md, file_2.md) to make it unique.
    """
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    
    # While a file with this name exists, keep adding numbers
    while (directory / new_filename).exists():
        new_filename = f"{name}_{counter}{ext}"
        counter += 1
        
    return new_filename

def main():
    start_time = datetime.now()
    base_path = Path.cwd()
    src_path = base_path / SOURCE_DIR
    out_path = base_path / OUTPUT_DIR
    
    if not src_path.exists():
        print(f"❌ CRITICAL ERROR: Folder '{SOURCE_DIR}' not found.")
        sys.exit(1)

    if out_path.exists():
        shutil.rmtree(out_path)
    
    (out_path / LOGSEQ_ASSETS).mkdir(parents=True, exist_ok=True)
    (out_path / LOGSEQ_PAGES).mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting Migration (Anti-Duplicate + Sanitizer Mode) in: {base_path}")
    print("---------------------------------------------------")

    # ---------------------------------------------------------
    # PHASE 1: IMAGES
    # ---------------------------------------------------------
    src_resources = src_path / JOPLIN_RESOURCES
    dest_assets = out_path / LOGSEQ_ASSETS
    assets_count = 0
    
    if src_resources.exists():
        print(f"📦 Moving image library...")
        files = [f for f in src_resources.iterdir() if f.is_file()]
        for item in files:
            shutil.copy2(item, dest_assets / item.name)
            assets_count += 1
        print(f"✅ PHASE 1 COMPLETE: {assets_count} images copied.")
    else:
        print("⚠️ WARNING: '_resources' folder not found.")

    # ---------------------------------------------------------
    # PHASE 2: NOTES
    # ---------------------------------------------------------
    print("---------------------------------------------------")
    print("📝 Processing notes...")
    
    notes_found = 0
    notes_processed = 0
    notes_failed = []

    pages_dir = out_path / LOGSEQ_PAGES

    for root, dirs, files in os.walk(src_path):
        if JOPLIN_RESOURCES in dirs:
            dirs.remove(JOPLIN_RESOURCES)
        
        for file in files:
            if file.endswith(".md"):
                notes_found += 1
                try:
                    original_file_path = Path(root) / file
                    
                    # 1. Flatten Namespace
                    rel_path = original_file_path.relative_to(src_path)
                    if rel_path.parent.parts:
                        base_name = "___".join(rel_path.parent.parts) + "___" + file
                    else:
                        base_name = file
                    
                    # --- FIX: Remove double dots (..md -> .md) ---
                    # This forces the filename to match the "clean" version.
                    # Since the clean version might already exist, get_unique_filename below
                    # will automatically rename this one to _1.md, _2.md, etc.
                    if base_name.endswith("..md"):
                         base_name = base_name[:-4] + ".md"
                    
                    # 2. ANTI-DUPLICATE MAGIC
                    unique_name = get_unique_filename(pages_dir, base_name)
                    dest_file_path = pages_dir / unique_name

                    # 3. Read content
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 4. Transformations
                    content = clean_frontmatter(content)
                    content = re.sub(r'\((?:\.\./)?_resources/', '(../assets/', content)
                    content = re.sub(r'<br class="jop-noMdConv">', '', content)

                    # 5. Write content
                    with open(dest_file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    notes_processed += 1
                    
                except Exception as e:
                    print(f"❌ Error in note: {file} -> {e}")
                    notes_failed.append(file)

    # ---------------------------------------------------------
    # PHASE 3: SUMMARY
    # ---------------------------------------------------------
    duration = datetime.now() - start_time
    print("---------------------------------------------------")
    print(f"🏁 DONE in {duration}")
    print(f"📂 Output: {out_path}")
    print(f"✅ Notes Created: {notes_processed}/{notes_found}")
    
    if notes_failed:
        print(f"❌ Failed: {len(notes_failed)}")

if __name__ == "__main__":
    main()