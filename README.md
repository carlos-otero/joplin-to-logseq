# Joplin to Logseq Importer (Python)

A robust Python script to migrate your notes from **Joplin** to **Logseq**, preserving your folder hierarchy (using namespaces), fixing image links, and cleaning up metadata.

This is a Python-based fork/rewrite inspired by [dasrecht/joplin-to-logseq-importer](https://github.com/dasrecht/joplin-to-logseq-importer).

## 🚀 Features

- **Namespace Flattening:** Converts Joplin folder structures (e.g., `Personal/Work/Note.md`) into Logseq-compatible namespaces (e.g., `Personal___Work___Note.md`).
- **Asset Migration:** Automatically finds and moves all images/attachments from `_resources` to Logseq's `assets` folder.
- **Link Fixing:** Updates all Markdown links in your notes to point correctly to the new `../assets/` location.
- **Metadata Cleanup:** Removes unnecessary Joplin frontmatter (GPS coordinates, internal IDs, etc.) while keeping and formatting `#tags` correctly for Logseq (`tags::`).
- **Integrity Check:** Provides a detailed summary report ensuring 100% of your notes and images were processed.

## 📋 Prerequisites

- **Python 3** (Pre-installed on most Linux/macOS systems. Available for Windows on the Microsoft Store).

## 🛠️ Usage Guide

### 1. Export from Joplin
1. Open Joplin on your computer.
2. Go to **File > Export all > MD - Markdown + Front Matter**.
3. Create a folder named `joplin-input` in the same directory as this script.
4. Save the export inside that folder.

Your structure should look like this:
```
/joplin-to-logseq-importer
    ├── migrate.py
    └── joplin-input/
        ├── _resources/
        ├── Notebook A/
        └── Notebook B/
2. Run the Script
```

🐧 Linux / 🍏 macOS
Open your terminal, navigate to the folder, and run:

```
python3 migrate.py
```

🪟 Windows
Open PowerShell or Command Prompt, navigate to the folder, and run:

```
python migrate.py
```

3. Import into Logseq
Once the script finishes, you will see a new folder named logseq-output.

Inside, you will find pages and assets.

Copy the contents of logseq-output directly into your main Logseq graph folder.

Note: If asked, merge the folders.

Open Logseq and "Re-index" your graph to see your new notes!

⚠️ Disclaimer
Always backup your data before performing mass migrations. This script is provided "as is" without warranty of any kind.
