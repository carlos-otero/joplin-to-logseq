# 📂 Joplin to Logseq Migration Tools

Conjunto de scripts en Python para migrar una base de conocimientos completa desde **Joplin** (archivos `.md` exportados) hacia **Logseq**, preservando jerarquías, fechas y limpiando el formato.

## 🚀 Scripts Incluidos

### 1. `migrate.py` (v3.2) - El Migrador Principal
Este script toma la exportación "RAW" de Joplin y la transforma en un grafo listo para Logseq.

**Características Clave:**
* **Jerarquías y Namespaces:** Convierte la estructura de carpetas de Joplin en namespaces de Logseq (ej: `Carpeta/Nota` → archivo `Carpeta.Nota.md` con propiedad `title:: Carpeta/Nota`).
* **Gestión de Workflow:** Añade automáticamente los tags `[[Joplin]]` y `[[Por Procesar]]` para facilitar la revisión posterior.
* **Limpieza Profunda:**
    * Elimina metadatos basura de Joplin (`id`, `latitude`, `source_url`, etc.).
    * Limpia entidades HTML residuales como `&nbsp;`, `&tbsp;` y `<br>`.
* **Reparación de Enlaces:**
    * Aplana las rutas de imágenes y PDFs: `../../_resources/img.png` → `../assets/img.png`.
    * Convierte enlaces Markdown estándar `[Texto](Nota.md)` en Wikilinks `[[Nota]]`.
* **Fechas:** Preserva la fecha de creación original (`created-at` timestamp) y añade enlace al Journal (`date`).
* **Índice Maestro:** Genera un archivo `000_Indice_Migracion.md` con el listado de todo lo importado.
* **Tareas:** Respeta los checkboxes originales (`- [ ]`) sin convertirlos forzosamente a `TODO/DONE`.

### 2. `auto_tagger.py` - Etiquetado con IA (Opcional)
Script complementario que usa Google Gemini (Flash 2.0) para leer tus notas ya migradas y añadirles:
* Tags semánticos (ej: `tags:: [[Productividad]], [[Python]]`).
* Un resumen de una frase (`ai-summary:: ...`).

---

## 🛠️ Instrucciones de Uso

### Paso 1: Preparación
1.  Exporta tus notas de Joplin en formato **Markdown + Frontmatter**.
2.  Coloca la carpeta exportada como `joplin-input` en la raíz de este proyecto.
3.  Asegúrate de tener Python instalado.

### Paso 2: Ejecutar Migración
```
python migrate.py
```

El resultado aparecerá en la carpeta logseq-output.

Paso 3: (Opcional) Etiquetado IA
Crea un archivo api_key.txt con tu clave de Google Gemini.

Ejecuta:

```

python auto_tagger.py

```

Paso 4: Importar en Logseq
Mueve el contenido de logseq-output a tu carpeta de grafo de Logseq.

En Logseq, ve a Settings > Re-index graph.

Busca la página [[Por Procesar]] para empezar a organizar tus notas.

📋 Requisitos

Python 3.8+

Librerías (solo para el auto_tagger):

```

pip install google-generativeai

```