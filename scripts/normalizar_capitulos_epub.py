from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


CHAPTER_LINE_RE = re.compile(
    r'^\s*(?:#+\s*)?Cap[ií]tulo\s+(\d+)\s*[:：.-]\s*(.+?)\s*\.?\s*$',
    re.IGNORECASE
)

FILENAME_CHAPTER_RE = re.compile(r'第(\d+)章')

CHINESE_NUM_MAP = {
    "（一）": "I",
    "（二）": "II",
    "（三）": "III",
    "（四）": "IV",
    "（五）": "V",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_original_global_from_filename(path: Path) -> int | None:
    m = FILENAME_CHAPTER_RE.search(path.name)
    if m:
        return int(m.group(1))
    return None


def renumber_from_filename(path: Path) -> int | None:
    original = extract_original_global_from_filename(path)
    if original is None:
        return None
    new_num = original - 4
    return new_num if new_num > 0 else None


def clean_title_text(title: str) -> str:
    title = title.strip().strip(".:：-–— ")
    title = re.sub(r"\s+", " ", title)
    return title


def title_case_fixes(title: str) -> str:
    # Ajustes opcionales simples
    title = title.replace("Clark", "Kraak")  # si preferís Kraak en vez de Clark
    for zh, roman in CHINESE_NUM_MAP.items():
        title = title.replace(zh, roman)
    return title


def find_h2_title(lines: list[str]) -> tuple[int, str] | None:
    """
    Busca un encabezado ## Capítulo ...
    Devuelve (índice de línea, texto del título)
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("##"):
            m = CHAPTER_LINE_RE.match(stripped)
            if m:
                num = int(m.group(1))
                title = clean_title_text(m.group(2))
                return i, f"Capítulo {num}: {title}"
    return None


def find_last_chapter_title_anywhere(lines: list[str]) -> tuple[int, str] | None:
    """
    Si no hay ## Capítulo ..., toma la ÚLTIMA línea del archivo
    que parezca título de capítulo.
    """
    last_match = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = CHAPTER_LINE_RE.match(stripped)
        if m:
            num = int(m.group(1))
            title = clean_title_text(m.group(2))
            last_match = (i, f"Capítulo {num}: {title}")
    return last_match


def build_final_h2(path: Path, detected_title: str | None) -> str:
    """
    Construye el encabezado final '## Capítulo X: ...'
    usando:
    - el número renumerado desde filename
    - el título detectado en el texto si existe
    """
    new_num = renumber_from_filename(path)

    if detected_title:
        m = re.match(r'^Cap[ií]tulo\s+(\d+)\s*[:：.-]\s*(.+)$', detected_title, re.IGNORECASE)
        if m:
            title_part = title_case_fixes(clean_title_text(m.group(2)))
            if new_num is not None:
                return f"## Capítulo {new_num}: {title_part}"
            return f"## Capítulo {int(m.group(1))}: {title_part}"

    # fallback bruto si no detecta título
    stem = path.stem
    # saca prefijos comunes
    stem = re.sub(r'^\d+-', '', stem)
    stem = re.sub(r'^第\d+章-', '', stem)
    stem = stem.replace('_es_clean', '').replace('_es', '')
    title_part = title_case_fixes(clean_title_text(stem))
    if new_num is not None:
        return f"## Capítulo {new_num}: {title_part}"
    return f"## {title_part}"


def strip_before_index(lines: list[str], start_idx: int) -> list[str]:
    return lines[start_idx:]


def remove_duplicate_initial_title_lines(lines: list[str], final_h2: str) -> list[str]:
    """
    Después de insertar el H2 final, elimina duplicados inmediatos
    tipo:
      ## Capítulo 4: X
      Capítulo 4: X
      # Capítulo 4: X
    """
    if not lines:
        return lines

    target = re.sub(r'^##\s*', '', final_h2).strip().lower().rstrip(".")
    cleaned = []
    skipped_once = False

    for i, line in enumerate(lines):
        if i == 0:
            cleaned.append(line)
            continue

        simplified = re.sub(r'^#+\s*', '', line.strip()).lower().rstrip(".")
        if simplified == target and not skipped_once:
            skipped_once = True
            continue

        cleaned.append(line)

    return cleaned


def normalize_file(path: Path) -> str:
    text = normalize_newlines(read_text(path))
    lines = text.split("\n")

    # Caso 1: ya existe un ## Capítulo ...
    h2 = find_h2_title(lines)
    if h2:
        idx, detected = h2
        kept = strip_before_index(lines, idx)
        final_h2 = build_final_h2(path, detected)
        kept[0] = final_h2
        kept = remove_duplicate_initial_title_lines(kept, final_h2)
        return "\n".join(kept).strip() + "\n"

    # Caso 2: no existe ##, usar el último título de capítulo del archivo
    last_title = find_last_chapter_title_anywhere(lines)
    if last_title:
        idx, detected = last_title
        body = strip_before_index(lines, idx + 1)  # borrar también esa línea original
        final_h2 = build_final_h2(path, detected)
        new_lines = [final_h2, ""] + body
        new_lines = remove_duplicate_initial_title_lines(new_lines, final_h2)
        return "\n".join(new_lines).strip() + "\n"

    # Caso 3: fallback bruto
    final_h2 = build_final_h2(path, None)
    return final_h2 + "\n\n" + text.strip() + "\n"


def iter_md_files(path: Path) -> Iterable[Path]:
    if path.is_file() and path.suffix.lower() == ".md":
        yield path
        return
    if path.is_dir():
        for p in sorted(path.glob("*.md")):
            yield p


def output_path_for_file(p: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return p.with_name(f"{p.stem}_epub{p.suffix}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{p.stem}_epub{p.suffix}"


def process_file(path: Path, output_dir: Path | None) -> Path:
    normalized = normalize_file(path)
    out = output_path_for_file(path, output_dir)
    write_text(out, normalized)
    print(f"[OK] {path.name} -> {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normaliza capítulos para EPUB: resta 4 al número, deja solo un ## Capítulo..., y borra texto anterior."
    )
    parser.add_argument("path", help="Archivo .md o carpeta")
    parser.add_argument("--output-dir", default=None, help="Carpeta de salida")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        raise FileNotFoundError(f"No existe la ruta: {target}")

    output_dir = Path(args.output_dir) if args.output_dir else None

    files = list(iter_md_files(target))
    if not files:
        raise FileNotFoundError("No se encontraron archivos .md")

    for f in files:
        process_file(f, output_dir)


if __name__ == "__main__":
    main()