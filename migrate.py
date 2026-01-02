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
    "type_"
]

def clean_frontmatter(content):
    """
    Parses the YAML block (between ---) and removes unwanted lines.
    Converts Joplin 'tags:' to Logseq 'tags::'.
    """
    # Regex to capture the YAML block at the start of the file
    yaml_pattern = r"^---\n(.*?)\n---\n"
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    if not match:
        return content # No metadata found, return original content

    original_block = match.group(1)
    new_lines = []
    
    for line in original_block.split('\n'):
        # Ignore empty lines
        if not line.strip():
            continue
            
        key = line.split(':')[0].strip()
        
        # Skip if key is in the blacklist
        if key in METADATA_BLACKLIST:
            continue
            
        # Convert tags to Logseq property format
        if key == "tags":
            # Joplin: tags: tag1, tag2
            # Logseq: tags:: tag1, tag2
            line = line.replace("tags:", "tags::")
        
        new_lines.append(line)

    # Rebuild the block
    if not new_lines:
        # If we deleted everything, remove the block entirely
        return re.sub(yaml_pattern, "", content)
    
    new_block = "---\n" + "\n".join(new_lines) + "\n---\n"
    return content.replace(match.group(0), new_block)

def main():
    start_time = datetime.now()
    base_path = Path.cwd()
    src_path = base_path / SOURCE_DIR
    out_path = base_path / OUTPUT_DIR
    
    # 1. Pre-checks
    if not src_path.exists():
        print(f"❌ CRITICAL ERROR: Folder '{SOURCE_DIR}' not found.")
        print("   Please make sure you are in the correct directory and 'joplin-input' exists.")
        sys.exit(1)

    # Initial cleanup
    if out_path.exists():
        shutil.rmtree(out_path)
    
    (out_path / LOGSEQ_ASSETS).mkdir(parents=True, exist_ok=True)
    (out_path / LOGSEQ_PAGES).mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting Migration in: {base_path}")
    print("---------------------------------------------------")

    # ---------------------------------------------------------
    # PHASE 1: IMAGES (Brute Force Guarantee)
    # ---------------------------------------------------------
    src_resources = src_path / JOPLIN_RESOURCES
    dest_assets = out_path / LOGSEQ_ASSETS
    assets_count = 0
    
    if src_resources.exists():
        print(f"📦 Moving image library...")
        # Iterate and copy
        files = [f for f in src_resources.iterdir() if f.is_file()]
        total_assets = len(files)
        
        for item in files:
            shutil.copy2(item, dest_assets / item.name)
            assets_count += 1
            # Simple progress bar
            if assets_count % 100 == 0:
                print(f"   ...copied {assets_count}/{total_assets} files")
                
        print(f"✅ PHASE 1 COMPLETE: {assets_count} images copied to 'assets'.")
    else:
        print("⚠️ WARNING: '_resources' folder not found. Assuming no images to migrate.")

    # ---------------------------------------------------------
    # PHASE 2: NOTES (Processing & Cleanup)
    # ---------------------------------------------------------
    print("---------------------------------------------------")
    print("📝 Processing notes (Metadata cleanup + Re-linking)...")
    
    notes_found = 0
    notes_processed = 0
    notes_failed = []

    for root, dirs, files in os.walk(src_path):
        if JOPLIN_RESOURCES in dirs:
            dirs.remove(JOPLIN_RESOURCES) # Don't enter the image folder
        
        for file in files:
            if file.endswith(".md"):
                notes_found += 1
                try:
                    original_file_path = Path(root) / file
                    
                    # Calculate flattened name (Namespace)
                    rel_path = original_file_path.relative_to(src_path)
                    if rel_path.parent.parts:
                        new_filename = "___".join(rel_path.parent.parts) + "___" + file
                    else:
                        new_filename = file
                    
                    dest_file_path = out_path / LOGSEQ_PAGES / new_filename

                    # READ
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # TRANSFORMATIONS
                    # 1. Clean Frontmatter (GPS, IDs, etc)
                    content = clean_frontmatter(content)
                    
                    # 2. Fix image links
                    # Change any variant of (_resources/img) to (../assets/img)
                    content = re.sub(r'\((?:\.\./)?_resources/', '(../assets/', content)
                    
                    # 3. Remove HTML garbage sometimes left by Joplin
                    content = re.sub(r'<br class="jop-noMdConv">', '', content)

                    # SAVE
                    with open(dest_file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    notes_processed += 1
                    
                except Exception as e:
                    print(f"❌ Error in note: {file} -> {e}")
                    notes_failed.append(file)

    # ---------------------------------------------------------
    # PHASE 3: FINAL REPORT AND CHECK
    # ---------------------------------------------------------
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("---------------------------------------------------")
    print("🏁 FINAL OPERATION SUMMARY")
    print("---------------------------------------------------")
    print(f"⏱️  Total Time: {duration}")
    print(f"📂 Output Folder: {out_path}")
    print(f"📸 Images Migrated: {assets_count}")
    print(f"📄 Notes Found:     {notes_found}")
    print(f"✅ Notes Created:   {notes_processed}")
    
    if notes_found == notes_processed:
        print("\n✨ PERFECT INTEGRITY: 100% of notes have been migrated.")
    else:
        print(f"\n⚠️  ATTENTION: {notes_found - notes_processed} notes are missing.")
    
    if notes_failed:
        print("❌ Files with errors:")
        for fail in notes_failed:
            print(f"   - {fail}")
    
    print("\n👉 Next Step: Copy the contents of 'logseq-output' into your Logseq graph folder.")

if __name__ == "__main__":
    main()