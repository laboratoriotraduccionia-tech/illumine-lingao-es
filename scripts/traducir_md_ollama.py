from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "translategemma:12b"


SYSTEM_PROMPT = """Translate from Mandarin Chinese to Spanish.

Strict rules:
- Keep all proper names in pinyin.
- Do not translate names into meanings.
- Do not split pinyin names.
- Do not leave Chinese characters in the output.
- Preserve markdown structure exactly.
- Do not add explanations, notes, or code fences.
- Use natural, neutral Spanish.
- Convert all recurring Chinese names and place names directly to fixed pinyin.
- Do not keep Chinese characters in parentheses.
- Do not output markdown code fences like ```markdown.
- Keep author names as pinyin, never translate their literal meaning.
- Use these fixed translations for this book:
得不偿失 = Debuchangshi
穿越众 = viajeros temporales
常某 = yo, Chang
常师德 = Chang Shide
文德嗣 = Wen Desi
萧子山 = Xiao Zishan
王洛宾 = Wang Luobin
高举 = Gao Ju
临高 = Lingao
雷州 = Leizhou
广州 = Guangzhou
海南 = Hainan
台湾 = Taiwan
文总 = Wen Zong
高老爷 = señor Gao
红楼梦 = Sueño en el pabellón rojo

Return only the final translated text.
"""


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def post_ollama(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Respuesta inesperada de Ollama: {data}")
    return data


def ollama_unload_model(model: str, url: str, timeout: int) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": "",
        "stream": False,
        "keep_alive": 0,
    }
    return post_ollama(url, payload, timeout)


def ollama_load_model(
    model: str,
    url: str,
    timeout: int,
    keep_alive: Optional[str | int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": "",
        "stream": False,
    }
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    return post_ollama(url, payload, timeout)


def refresh_model(
    model: str,
    url: str,
    timeout: int,
    keep_alive: Optional[str | int],
    reason: str,
) -> None:
    print(f"[{now_str()}] Refresh del modelo ({reason}) - descargando {model}...", file=sys.stderr, flush=True)
    try:
        unload_resp = ollama_unload_model(model=model, url=url, timeout=timeout)
        print(
            f"[{now_str()}] Descarga completada: done_reason={unload_resp.get('done_reason')} model={unload_resp.get('model')}",
            file=sys.stderr,
            flush=True,
        )
    except Exception as exc:
        print(f"[{now_str()}] Aviso: no se pudo descargar el modelo: {exc}", file=sys.stderr, flush=True)

    print(f"[{now_str()}] Refresh del modelo ({reason}) - precargando {model}...", file=sys.stderr, flush=True)
    t0 = time.perf_counter()
    load_resp = ollama_load_model(model=model, url=url, timeout=timeout, keep_alive=keep_alive)
    elapsed = time.perf_counter() - t0
    print(
        f"[{now_str()}] Precarga completada en {elapsed:.2f}s: done_reason={load_resp.get('done_reason')} model={load_resp.get('model')}",
        file=sys.stderr,
        flush=True,
    )


def call_ollama(
    prompt: str,
    model: str,
    temperature: float = 0.2,
    num_ctx: int = 8192,
    timeout: int = 900,
    retries: int = 3,
    retry_wait: float = 5.0,
    url: str = OLLAMA_URL,
    keep_alive: Optional[str | int] = None,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
        },
    }
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive

    last_err: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            data = post_ollama(url, payload, timeout)
            if "response" not in data:
                raise RuntimeError(f"Respuesta inesperada de Ollama: {data}")
            return str(data["response"]).strip()
        except Exception as exc:
            last_err = exc
            print(
                f"[{now_str()}] [WARN] intento {attempt}/{retries} falló: {exc}",
                file=sys.stderr,
                flush=True,
            )
            if attempt < retries:
                time.sleep(retry_wait)

    raise RuntimeError(f"Falló la llamada a Ollama tras {retries} intentos: {last_err}")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_blocks(md_text: str) -> list[str]:
    text = normalize_newlines(md_text)
    lines = text.split("\n")

    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append("\n".join(current).rstrip())
            current = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            flush()
            blocks.append(line)
            continue

        if re.fullmatch(r"-{3,}", stripped):
            flush()
            blocks.append(line)
            continue

        if stripped.startswith("#"):
            flush()
            blocks.append(line)
            continue

        if stripped == "":
            flush()
            blocks.append("")
            continue

        current.append(line)

    flush()
    return blocks


def is_translatable(block: str) -> bool:
    stripped = block.strip()
    if not stripped:
        return False
    if stripped.startswith("<!--") and stripped.endswith("-->"):
        return False
    if re.fullmatch(r"-{3,}", stripped):
        return False
    return True


def mostly_chinese(text: str) -> bool:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]", text))
    return cjk > 0 and cjk >= latin


def chunk_text(text: str, max_chars: int = 1400) -> list[str]:
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current = ""

    for p in paragraphs:
        candidate = p if not current else current + "\n" + p
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(p) <= max_chars:
                current = p
            else:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i:i + max_chars])
                current = ""

    if current:
        chunks.append(current)

    return chunks


def translate_block(
    block: str,
    model: str,
    pause: float = 0.0,
    timeout: int = 900,
    retries: int = 3,
    retry_wait: float = 5.0,
    num_ctx: int = 8192,
    url: str = OLLAMA_URL,
    keep_alive: Optional[str | int] = None,
) -> str:
    if not is_translatable(block):
        return block

    if not mostly_chinese(block) and not block.lstrip().startswith("#"):
        return block

    chunks = chunk_text(block)
    translated_chunks: list[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        prompt = (
            "Traducí el siguiente fragmento de Markdown del chino mandarín al español.\n"
            "Mantené nombres propios en pinyin y respetá el formato.\n\n"
            f"{chunk}"
        )
        translated = call_ollama(
            prompt=prompt,
            model=model,
            timeout=timeout,
            retries=retries,
            retry_wait=retry_wait,
            num_ctx=num_ctx,
            url=url,
            keep_alive=keep_alive,
        )
        translated_chunks.append(translated)

        if pause > 0 and idx < len(chunks):
            time.sleep(pause)

    return "\n".join(translated_chunks)


def translate_markdown(
    md_text: str,
    model: str,
    pause: float = 0.0,
    timeout: int = 900,
    retries: int = 3,
    retry_wait: float = 5.0,
    num_ctx: int = 8192,
    url: str = OLLAMA_URL,
    keep_alive: Optional[str | int] = None,
) -> str:
    blocks = split_blocks(md_text)
    out_blocks: list[str] = []

    total = len(blocks)
    for i, block in enumerate(blocks, start=1):
        print(f"[{i}/{total}] procesando bloque...", file=sys.stderr, flush=True)
        out_blocks.append(
            translate_block(
                block,
                model=model,
                pause=pause,
                timeout=timeout,
                retries=retries,
                retry_wait=retry_wait,
                num_ctx=num_ctx,
                url=url,
                keep_alive=keep_alive,
            )
        )

    result_lines: list[str] = []
    for block in out_blocks:
        if block == "":
            result_lines.append("")
        else:
            result_lines.append(block)

    return "\n".join(result_lines).strip() + "\n"


def output_name(input_path: Path, suffix: str) -> Path:
    return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


def process_file(
    input_path: Path,
    model: str,
    suffix: str,
    pause: float,
    timeout: int,
    retries: int,
    retry_wait: float,
    num_ctx: int,
    url: str,
    keep_alive: Optional[str | int],
) -> Path:
    text = input_path.read_text(encoding="utf-8")
    translated = translate_markdown(
        text,
        model=model,
        pause=pause,
        timeout=timeout,
        retries=retries,
        retry_wait=retry_wait,
        num_ctx=num_ctx,
        url=url,
        keep_alive=keep_alive,
    )
    out_path = output_name(input_path, suffix)
    out_path.write_text(translated, encoding="utf-8")
    return out_path


def iter_md_files(path: Path) -> Iterable[Path]:
    if path.is_file() and path.suffix.lower() == ".md":
        yield path
        return

    if path.is_dir():
        for p in sorted(path.rglob("*.md")):
            yield p


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Traduce archivos Markdown del chino al español usando Ollama."
    )
    parser.add_argument("path", help="Archivo .md o carpeta con archivos .md")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo de Ollama (default: {DEFAULT_MODEL})")
    parser.add_argument("--suffix", default="_es", help="Sufijo para el archivo traducido (default: _es)")
    parser.add_argument("--pause", type=float, default=0.2, help="Pausa entre chunks largos (default: 0.2)")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout por request a Ollama en segundos")
    parser.add_argument("--retries", type=int, default=3, help="Cantidad de reintentos por bloque")
    parser.add_argument("--retry-wait", type=float, default=5.0, help="Segundos entre reintentos")
    parser.add_argument("--num-ctx", type=int, default=8192, help="num_ctx para Ollama")
    parser.add_argument("--url", default=OLLAMA_URL, help=f"URL de Ollama (default: {OLLAMA_URL})")
    parser.add_argument(
        "--refresh-per-file",
        action="store_true",
        help="Descarga y precarga el modelo antes de cada archivo",
    )
    parser.add_argument(
        "--keep-alive",
        default="10m",
        help='keep_alive para Ollama (ej. "10m", 0, "0"). Default: 10m',
    )
    parser.add_argument(
        "--initial-preload",
        action="store_true",
        help="Precarga el modelo una vez al inicio",
    )
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        raise FileNotFoundError(f"No existe la ruta: {target}")

    keep_alive: Optional[str | int]
    if args.keep_alive in ("", "none", "None", "null"):
        keep_alive = None
    else:
        try:
            keep_alive = int(args.keep_alive)
        except ValueError:
            keep_alive = args.keep_alive

    md_files = list(iter_md_files(target))
    if not md_files:
        raise FileNotFoundError("No se encontraron archivos .md")

    print(f"Se encontraron {len(md_files)} archivo(s).", file=sys.stderr, flush=True)

    if args.initial_preload and not args.refresh_per_file:
        refresh_model(
            model=args.model,
            url=args.url,
            timeout=args.timeout,
            keep_alive=keep_alive,
            reason="inicio de corrida",
        )

    generated: list[Path] = []
    for idx, md_file in enumerate(md_files, start=1):
        if args.refresh_per_file:
            refresh_model(
                model=args.model,
                url=args.url,
                timeout=args.timeout,
                keep_alive=keep_alive,
                reason=f"cambio de archivo {idx}/{len(md_files)}: {md_file.name}",
            )

        print(f"\nTraduciendo: {md_file}", file=sys.stderr, flush=True)
        out = process_file(
            input_path=md_file,
            model=args.model,
            suffix=args.suffix,
            pause=args.pause,
            timeout=args.timeout,
            retries=args.retries,
            retry_wait=args.retry_wait,
            num_ctx=args.num_ctx,
            url=args.url,
            keep_alive=keep_alive,
        )
        generated.append(out)
        print(f"Generado: {out}", file=sys.stderr, flush=True)

    print("\nListo.", file=sys.stderr, flush=True)
    for g in generated:
        print(g)


if __name__ == "__main__":
    main()