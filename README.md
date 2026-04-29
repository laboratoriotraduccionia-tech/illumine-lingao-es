# El amanecer de Lingao (临高启明) – Traducción al Español

Traducción no oficial al español de la novela web china **临高启明 (Lingao Qiming)**.

---

## 📌 Sobre el proyecto

Este proyecto tiene como objetivo:

* Traducir la novela al español
* Mantener nombres propios en pinyin
* Preservar coherencia terminológica
* Generar versiones EPUB para lectura

---

## 📚 Fuente

Este proyecto se basa en:

* Archivos en inglés del repositorio:
  https://github.com/lpi/illuminelingao2

---

## ⚙️ Metodología

Pipeline de procesamiento:

1. Traducción automática con modelos locales (Ollama)
2. Post-procesamiento automático
3. Normalización estructural para EPUB
4. Revisión manual

Ejemplo de reglas de traducción:

* Nombres propios en pinyin (ej: Wen Desi, Xiao Zishan)
* Sin caracteres chinos en el resultado final
* Respeto estricto del formato Markdown

El script de traducción usa Ollama y modelos como:

* `translategemma:12b` 

---

## 🛠️ Requisitos

### 🔹 Software

* Python 3.10+
* Pandoc (para generar EPUB)
* Ollama (para traducción)

### 🔹 Python

Instalar dependencias:

```bash
pip install requests
```

---

## 🚀 Uso

### 1. Traducción

```bash
python scripts/traducir_md_ollama.py <carpeta_o_archivo>
```

### 2. Post-proceso

```bash
python scripts/postproceso_traduccion.py <carpeta_o_archivo>
```

Este paso:

* limpia texto basura
* aplica reemplazos consistentes
* detecta chino residual 

---

### 3. Normalización para EPUB

```bash
python scripts/normalizar_capitulos_epub.py <carpeta>
```

Este script:

* renumera capítulos
* elimina duplicaciones
* deja un único `## Capítulo X` por archivo 

---

### 4. Generar EPUB

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_epub.ps1
```

Requiere:

* Pandoc instalado
* Archivos organizados en `capitulos_espanol/`

---

## 📂 Estructura

* `capitulos_espanol/` → capítulos traducidos
* `scripts/` → pipeline de procesamiento
* `epub/` → versiones generadas

---

## ⚠️ Aviso legal

* Traducción **no oficial**
* Sin fines comerciales
* Todos los derechos pertenecen al autor original

---

## 🔗 Estado

Trabajo en progreso 🚧

---

## 🤝 Contribuciones

Se aceptan sugerencias, correcciones y mejoras.
