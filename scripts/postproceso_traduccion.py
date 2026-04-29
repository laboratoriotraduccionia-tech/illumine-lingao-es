from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


FIXED_REPLACEMENTS = {
    # nombres / autores
    "得不偿失": "Debuchangshi",
    "Dé no compensa lo perdido": "Debuchangshi",
    "Dé bù chángshī": "Debuchangshi",
    "Chang Shede": "Chang Shide",
    "Chang Shi de": "Chang Shide",
    "Chang Shi'de": "Chang Shide",
    "常师德": "Chang Shide",
    "张应宸": "Zhang Yingchen",
    "文德嗣": "Wen Desi",
    "萧子山": "Xiao Zishan",
    "王洛宾": "Wang Luobin",
    "高举": "Gao Ju",
    "文总": "Wen Zong",
    "高老爷": "señor Gao",
    "从天降鹰": "Cong Tian Jiang Ying",

    # nombres recurrentes nuevos
    "高青": "Gao Qing",
    "展无涯": "Zhan Wuya",
    "常凯申": "Chang Kaishen",
    "席亚洲": "Xi Yazhou",
    "姜野": "Jiang Ye",
    "北炜": "Bei Wei",
    "冉耀": "Ran Yao",
    "林深河": "Lin Shenhe",
    "郭逸": "Guo Yi",
    "利玛窦": "Matteo Ricci",

    # formas medio híbridas frecuentes
    "王工": "ingeniero Wang",
    "汪老大": "jefe Wang",
    "王头儿": "jefe Wang",

    # lugares
    "临高": "Lingao",
    "雷州": "Leizhou",
    "广州": "Guangzhou",
    "海南": "Hainan",
    "台湾": "Taiwan",
    "儋州": "Danzhou",

    # términos del libro
    "穿越众": "viajeros temporales",
    "红楼梦": "Sueño en el pabellón rojo",
    "常某": "yo, Chang",
    "Chang Mou": "yo, Chang",

    # términos / objetos / conceptos recurrentes
    "司马": "Sima",
    "拉羊头": "colgar cabeza de oveja",
    "人民币": "renminbi",
    "煤油树": "árbol del queroseno",
    "竹桐": "tungo de bambú",
    "臭油桐": "tungo hediondo",
    "黄连木": "pistacho chino",
    "五连发": "fusil de repetición de cinco disparos",
    "双环": "Shuanghuan",
    "天蚕宝甲": "armadura de seda celestial",
    "大量缝合线": "gran cantidad de hilo de sutura",
    "敷贴": "apósitos",
    "消毒液等等": "desinfectante, etcétera",
    "玻璃管注射器": "jeringas de vidrio",
    "纱布": "gasa",
    "防风打火机": "encendedor a prueba de viento",
    "...": "…",
    "SKS": "Tipo 56"
}

BAD_LINES_PATTERNS = [
    r"^\s*Aquí está la traducción al español:?\s*$",
    r"^\s*Claro, aquí está la traducción:?\s*$",
    r"^\s*Aquí tienes la traducción:?\s*$",
    r"^\s*Here is the translation:?\s*$",
    r"^\s*Return only the final translated text\.?\s*$",
]

KNOWN_TITLES = {
    "常师德对其指控的答辩": "La defensa de Chang Shide ante las acusaciones",
    "对其指控的答辩": "La defensa ante las acusaciones",
    "若干大结局": "Varios finales alternativos",
    "张应宸的关于新道教的同人": "Zhang Yingchen sobre el nuevo taoísmo",
    "的关于新道教的同人": "sobre el nuevo taoísmo",
    "临高启明演义版楔子": "Prólogo en versión novelada de Illumine Lingao",
    "启明演义版楔子": "Prólogo en versión novelada de Illumine Lingao",
}

IGNORE_RESIDUALS = {
    "众",
    "世纪",
    "人民币",
}

GLOSSARY_NOISE_TERMS = [
    "Debuchangshi",
    "viajeros temporales",
    "yo, Chang",
    "Chang Shide",
    "Wen Desi",
    "Xiao Zishan",
    "Wang Luobin",
    "Gao Ju",
    "Gao Qing",
    "Zhan Wuya",
    "Chang Kaishen",
    "Xi Yazhou",
    "Jiang Ye",
    "Bei Wei",
    "Ran Yao",
    "Lin Shenhe",
    "Guo Yi",
    "Matteo Ricci",
    "Lingao",
    "Leizhou",
    "Guangzhou",
    "Hainan",
    "Taiwan",
    "Danzhou",
    "Wen Zong",
    "señor Gao",
    "Sueño en el pabellón rojo",
]

CHAPTER_TITLE_RE = re.compile(
    r"^\s*第\s*([0-9０-９一二三四五六七八九十百千]+)\s*章\s*[:：]?\s*(.+?)\s*$"
)


def chinese_num_to_int(s: str) -> str:
    s = s.strip()
    fw_map = str.maketrans("０１２３４５６７８９", "0123456789")
    s = s.translate(fw_map)

    if s.isdigit():
        return s

    mapping = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
        "十": 10, "百": 100, "千": 1000
    }

    if s == "十":
        return "10"

    total = 0
    try:
        if "千" in s:
            parts = s.split("千")
            left = mapping.get(parts[0], 1) if parts[0] else 1
            total += left * 1000
            s = parts[1]

        if "百" in s:
            parts = s.split("百")
            left = mapping.get(parts[0], 1) if parts[0] else 1
            total += left * 100
            s = parts[1]

        if "十" in s:
            parts = s.split("十")
            left = mapping.get(parts[0], 1) if parts[0] else 1
            total += left * 10
            s = parts[1]

        if s:
            total += mapping[s]

        return str(total) if total > 0 else s
    except Exception:
        return s


def remove_code_fences(text: str) -> str:
    text = text.replace("```markdown", "")
    text = text.replace("```md", "")
    text = text.replace("```", "")
    return text


def remove_bad_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if any(re.match(pat, line.strip(), flags=re.IGNORECASE) for pat in BAD_LINES_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def apply_fixed_replacements(text: str) -> str:
    for src, dst in FIXED_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text


def normalize_known_parentheses(text: str) -> str:
    text = re.sub(r"雷州\s*[（(]\s*Leizhou\s*[）)]", "Leizhou", text, flags=re.IGNORECASE)
    text = re.sub(r"临高\s*[（(]\s*Lingao\s*[）)]", "Lingao", text, flags=re.IGNORECASE)
    text = re.sub(r"穿越众\s*[（(]\s*viajeros temporales\s*[）)]", "viajeros temporales", text, flags=re.IGNORECASE)
    text = re.sub(r"文\s*[（(]\s*Wen\s*[）)]", "Wen", text, flags=re.IGNORECASE)
    return text


def normalize_chapter_titles(text: str) -> str:
    lines = text.splitlines()
    out = []

    for line in lines:
        stripped = line.strip()
        m = CHAPTER_TITLE_RE.match(stripped)
        if m:
            num_raw = m.group(1)
            title_raw = m.group(2).strip()

            num = chinese_num_to_int(num_raw)
            title = KNOWN_TITLES.get(title_raw, title_raw)

            for src, dst in FIXED_REPLACEMENTS.items():
                title = title.replace(src, dst)

            line = f"Capítulo {num}: {title}"

        out.append(line)

    return "\n".join(out)


def remove_glossary_noise_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            cleaned.append(line)
            continue

        if stripped.startswith("#") or stripped.startswith("Capítulo"):
            cleaned.append(line)
            continue

        hits = sum(1 for term in GLOSSARY_NOISE_TERMS if term in stripped)
        if hits >= 4:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def simplify_title_line(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = s.rstrip(".:： ")
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def normalize_duplicate_title_lines(text: str) -> str:
    lines = text.splitlines()
    out = []
    prev_title = None

    for line in lines:
        current = line.strip()
        simplified = simplify_title_line(current)

        if simplified.startswith("capítulo "):
            if prev_title and simplified == prev_title:
                continue
            prev_title = simplified
        else:
            prev_title = None

        out.append(line)

    return "\n".join(out)


def normalize_spacing(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip() + "\n"


def detect_remaining_chinese(text: str) -> list[str]:
    found = sorted(set(re.findall(r"[\u4e00-\u9fff]+", text)))
    return [x for x in found if x not in IGNORE_RESIDUALS]


def split_residuals(residuals: list[str]) -> tuple[list[str], list[str]]:
    simple = []
    problematic = []

    for r in residuals:
        # Si es corto, suele ser nombre, lugar o término simple
        if len(r) <= 4:
            simple.append(r)
        else:
            problematic.append(r)

    return simple, problematic


def classify_file(simple: list[str], problematic: list[str]) -> str:
    if not simple and not problematic:
        return "OK"
    if problematic:
        return "REVISAR"
    return "OBSERVAR"


def postprocess_translation(text: str) -> tuple[str, list[str], list[str], str]:
    text = remove_code_fences(text)
    text = remove_bad_lines(text)
    text = apply_fixed_replacements(text)
    text = normalize_known_parentheses(text)
    text = normalize_chapter_titles(text)
    text = remove_glossary_noise_lines(text)
    text = normalize_duplicate_title_lines(text)
    text = normalize_spacing(text)

    remaining = detect_remaining_chinese(text)
    simple, problematic = split_residuals(remaining)
    status = classify_file(simple, problematic)

    return text, simple, problematic, status


def output_path_for_file(p: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return p.with_name(f"{p.stem}_clean{p.suffix}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{p.stem}_clean{p.suffix}"


def process_file(path: str | Path, output_dir: Path | None = None) -> Path:
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    cleaned, simple, problematic, status = postprocess_translation(text)

    out_path = output_path_for_file(p, output_dir)
    out_path.write_text(cleaned, encoding="utf-8")

    print(f"[{status}] Archivo limpio: {out_path}")

    if simple:
        print("[OBSERVACION] Residuos simples:")
        for item in simple:
            print(" -", item)

    if problematic:
        print("[REVISAR] Frases sin traducir o bloque problemático:")
        for item in problematic:
            print(" -", item)

    if not simple and not problematic:
        print("[OK] No quedó chino residual.")

    return out_path


def iter_input_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() == ".md":
            yield path
        return

    if path.is_dir():
        for p in sorted(path.glob("*_es.md")):
            yield p


def main() -> None:
    parser = argparse.ArgumentParser(description="Postprocesa traducciones Markdown.")
    parser.add_argument("path", help="Archivo .md o carpeta")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Carpeta de salida opcional para los _clean.md",
    )
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        raise FileNotFoundError(f"No existe la ruta: {target}")

    output_dir = Path(args.output_dir) if args.output_dir else None

    files = list(iter_input_files(target))
    if not files:
        raise FileNotFoundError("No se encontraron archivos .md para procesar.")

    for f in files:
        process_file(f, output_dir=output_dir)


if __name__ == "__main__":
    main()