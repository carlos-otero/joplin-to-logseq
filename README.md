# 📂 Joplin to Logseq Migration Tools

A suite of Python scripts designed to migrate a complete knowledge base from **Joplin** (Markdown exports) to **Logseq**, preserving hierarchies, dates, and structure while enriching content with AI.

## 🚀 Included Scripts

### 1. `migrate.py` (v3.5) - The Main Migrator
Transforms the "RAW" export from Joplin into a Logseq-optimized graph.

**Key Features:**
* **Strict Sanitization:** Cleans illegal filenames (e.g., removes leading `:` or `..` from names like `: Carlos`).
* **Standard YAML Formatting:** Generates clean Frontmatter using standard syntax (`key: value`) compatible with Logseq, preventing duplicates.
* **Hierarchies (Namespaces):** Converts Joplin folder structures into Logseq namespaces (e.g., `Folder/Note` → file `Folder.Note.md` with `title: Folder/Note`).
* **Tag Management:** Merges original Joplin tags with migration management tags (`[[Joplin]]`, `[[To Process]]`) into a single line without duplicates.
* **Deep Cleaning:**
    * Removes junk metadata (`latitude`, `id`, `source_url`, etc.).
    * Cleans residual HTML entities (`&nbsp;`, `&tbsp;`, `<br>`).
* **Link Repair:**
    * Flattens attachment paths: `../../_resources/img.png` → `../assets/img.png`.
    * Converts standard Markdown links `[Text](Note.md)` into Wikilinks `[[Note]]`.
* **Dates:** Preserves the original creation date (`created-at` timestamp) and adds a Journal link (`date`).
* **Master Index:** Generates `000_Migration_Index.md` listing every imported file.

### 2. `auto_tagger.py` (v2.0) - AI Enrichment
Uses Google Gemini (Flash 2.0) to analyze migrated notes.

**Improvements:**
* **Smart Tag Merging:** Reads existing tags, adds AI suggestions, removes duplicates, and rewrites the `tags:` property cleanly.
* **Auto-Summary:** Adds an `ai-summary:` property with a one-sentence synthesis of the content.
* **No Duplicates:** Respects existing YAML format and prevents creating double properties.

---

## 🛠️ Usage Instructions

### Step 1: Preparation
1.  Export your Joplin notes in **Markdown + Frontmatter** format.
2.  Place the exported folder as `joplin-input` in the root of this project.
3.  Install dependencies (only required for auto_tagger):
    ```
    pip install google-generativeai
    ```

### Step 2: Run Migration
```
python migrate.py
```

This will sanitize names, restructure folders, and generate files in logseq-output.

Step 3: (Optional) AI Tagging
Create an api_key.txt file containing your Google Gemini API Key.

Run:

```
python auto_tagger.py
```

The script will read the clean notes and add semantic tags without breaking the format.

Step 4: Import to Logseq
Move the contents of logseq-output to your Logseq graph folder.

In Logseq, go to Settings > Re-index graph.

Search for the page [[To Process]] (or the tag you configured) to start organizing.

📋 Requirements
Python 3.8+

Google AI Studio Account (for the API Key)