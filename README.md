# 📂 Joplin to Logseq Migration Tools

A suite of Python scripts designed to migrate a complete knowledge base from **Joplin** to **Logseq** cleanly, preserving structure and enriching content with AI (Local or Cloud).

## 🚀 Included Scripts

### 1. `migrate.py` (v3.5) - The Main Migrator
Transforms the "RAW" Joplin export into a Logseq-optimized graph.

**Key Features:**
* **Strict Sanitization:** Cleans illegal filenames (removes leading `:`, `..`, etc.).
* **Standard YAML Formatting:** Generates clean Frontmatter (`key: value`), avoiding obsolete `::` syntax and duplicates.
* **Hierarchies (Namespaces):** Converts Joplin folders into Logseq namespaces (e.g., `Folder.Note.md`) and injects the `title` property.
* **Tag Management:** Merges original tags with migration tags (`[[Joplin]]`, `[[To Process]]`) into a single line.
* **Deep Cleaning:** Removes junk metadata and cleans HTML entities (`&nbsp;`).
* **Link Repair:** Flattens attachment paths and converts Markdown links to Wikilinks.
* **Master Index:** Generates `000_Migration_Index.md`.

### 2. `auto_tagger.py` (v3.1) - Hybrid AI Enrichment
Interactive script to analyze notes, add semantic tags, and generate summaries.

**New in v3.1:**
* **Robust Parser (Regex):** Capable of understanding "messy" AI responses (asterisks, wrong formatting), significantly reducing errors.
* **Hybrid Mode:** Interactive menu to choose between **Ollama (Local/Private)** or **Gemini (Cloud/Fast)**.
* **Reinforced Prompt:** Instructions now include visual examples to enforce strict output formatting.

---

## 🛠️ Usage Instructions

### Step 1: Preparation
1.  Export your Joplin notes (Markdown + Frontmatter).
2.  Place the exported folder as `joplin-input` in the root directory.

### Step 2: Run Migration
```
python migrate.py
```

### Step 3: AI Tagging (Optional)
Run the script and follow the menu instructions:
```
python auto_tagger.py
```

* **Option 1 (Ollama):** Requires Ollama installed and the `llama3.1` model (`ollama pull llama3.1`).
* **Option 2 (Gemini):** Requires `api_key.txt` and the `google-generativeai` library.

### Step 4: Import to Logseq
1.  Move the contents of `logseq-output` to your Logseq graph folder.
2.  **Re-index graph** in Logseq settings.
3.  Start organizing from the `[[To Process]]` page.

---

## 📋 Requirements
* Python 3.8+
* **For Local Mode:** Ollama installed + `pip install ollama`
* **For Cloud Mode:** `pip install google-generativeai` + API Key.