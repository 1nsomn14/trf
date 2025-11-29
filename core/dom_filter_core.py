# core/dom_filter_core.py
import os
import re
import sys
import time
import asyncio
import aiofiles
from aiofiles.os import wrap
from asyncio import Lock as AsyncLock

async_makedirs = wrap(os.makedirs)
_lock = AsyncLock()

_INSTITUTION_KEYWORDS = [
    "kemdikbud","kemenkeu","kpu","pajak","bpk","kemkominfo","kemenkes",
    "kemenag","polri","kejaksaan","bkkbn","diknas","perhubungan","pertanian",
    "perdagangan","keuangan","mahkamah","bankindonesia","bpom","kemenkumham",
    "bppt","bappenas","bpbd","kemenlu","kemenpora","kominfo","sekretariat","setneg"
]

def ensure_dirs():
    os.makedirs("domlist", exist_ok=True)
    os.makedirs(os.path.join("results", "domfilter"), exist_ok=True)

def get_domlist_files(domlist_dir="domlist"):
    ensure_dirs()
    try:
        return [os.path.join(domlist_dir, f) for f in os.listdir(domlist_dir) if f.lower().endswith(".txt")]
    except Exception:
        return []

def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def _fix_protocol_spacing(line: str) -> str:
    line = re.sub(r'(?i)\bhttps?\s*[:]\s*//', lambda m: m.group(0).replace(" ", "").replace(":/","://"), line)
    line = re.sub(r'(?i)\bhttp\s*[:]\s*//', 'http://', line)
    line = re.sub(r'(?i)\bhttps\s*[:]\s*//', 'https://', line)
    return line

def _normalize_separators(line: str) -> str:
    line = _fix_protocol_spacing(line)
    line = re.sub(r'\|', ' | ', line)
    line = re.sub(r'(?<!:):(?!/)', ' : ', line)
    line = re.sub(r'\s*\|\s*', ' | ', line)
    line = re.sub(r'\s*:\s*', ' : ', line)
    line = re.sub(r'(?i)http\s*[:]\s*//', 'http://', line)
    line = re.sub(r'(?i)https\s*[:]\s*//', 'https://', line)
    return line.rstrip("\n")

def _match_filters(line: str, filter_keys: list) -> bool:
    if not filter_keys:
        return True
    l = line.lower()
    for key in filter_keys:
        k = key.strip().lower()
        if k == "kabupaten":
            if "kab.go.id" in l or "kabupaten." in l or re.search(r'\bkabupaten\b', l): return True
        elif k == "kota":
            if "kota.go.id" in l or re.search(r'\bkota\b', l): return True
        elif k == "prov":
            if "prov.go.id" in l or re.search(r'\w+prov\.go\.id', l) or "provinsi" in l: return True
        elif k == "instansi":
            if "go.id" in l and not any(x in l for x in ["kab.go.id","kota.go.id","prov.go.id"]):
                for inst in _INSTITUTION_KEYWORDS:
                    if inst in l: return True
                if re.search(r'\b(instansi|dept|office|sekretariat)\b', l): return True
        elif k in ("akademik","academic"):
            if ".ac.id" in l or ".edu.id" in l: return True
        elif k == "gov":
            if re.search(r'\.gov\.[a-z]{2,}(/|$)', l) and "go.id" not in l: return True
        elif k == "edu":
            if re.search(r'\.edu\.[a-z]{2,}(/|$)', l) and ".edu.id" not in l: return True
        elif k == "ac":
            if re.search(r'\.ac\.(in|th|uk|kr|my|za|ph|au|ng|pk|bd|jp|cn|sg|br|mx|us)(/|$)', l): return True
        else:
            if k and k in l: return True
    return False

async def _filter_single_file(path, filters, output_path, buffer_limit=5000, encoding='utf-8'):
    matched = 0
    buf = []
    async with aiofiles.open(path, "r", encoding=encoding, errors="ignore") as fin:
        async for line in fin:
            if _match_filters(line, filters):
                buf.append(_normalize_separators(line) + ("\n" if not line.endswith("\n") else ""))
                matched += 1
                if len(buf) >= buffer_limit:
                    async with _lock:
                        async with aiofiles.open(output_path, "a", encoding=encoding) as fout:
                            await fout.writelines(buf)
                    buf = []
    if buf:
        async with _lock:
            async with aiofiles.open(output_path, "a", encoding=encoding) as fout:
                await fout.writelines(buf)
    return os.path.basename(path), matched

async def process_files_async(input_files, filters, output_name,
                              domlist_dir="domlist", results_dir=None,
                              encoding='utf-8', concurrency=5, buffer_limit=5000, progress_cb=None):
    results_dir = results_dir or os.path.join("results", "domfilter")
    os.makedirs(results_dir, exist_ok=True)
    output_path = os.path.join(results_dir, output_name if output_name.endswith(".txt") else output_name + ".txt")

    # truncate output
    async with aiofiles.open(output_path, "w", encoding=encoding) as f:
        await f.write("\n")

    total_files = len(input_files)
    total_matched = 0
    start = time.time()

    sem = asyncio.Semaphore(concurrency)

    async def _worker(file):
        async with sem:
            return await _filter_single_file(file, filters, output_path, buffer_limit, encoding)

    tasks = [_worker(f) for f in input_files]
    done_count = 0
    for coro in asyncio.as_completed(tasks):
        try:
            name, matched = await coro
        except Exception as e:
            name, matched = "ERROR", 0
            sys.stdout.write(f"[ERROR] {e}\n")

        done_count += 1
        total_matched += matched
        elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - start))
        sys.stdout.write(f"[{elapsed}] {{ {name} }} -> {format_count(matched)} baris -> {done_count}/{total_files}\n")
        sys.stdout.flush()
        if progress_cb:
            try:
                progress_cb(done_count, total_files, total_matched)
            except Exception:
                pass

    sys.stdout.write(f"\n✅ Total hasil cocok: {format_count(total_matched)}\n")
    sys.stdout.write(f"📁 Disimpan di: {output_path}\n\n")
    sys.stdout.flush()
    return total_matched
