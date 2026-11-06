"""Sprawdza zdjęcia losowych produktów: wymiary w pikselach i rozmiar w KB.

Uruchomienie z katalogu scraper/:
    python check_images.py                       # 20 losowych produktów z results.json
    python check_images.py --seed 7              # to samo losowanie co poprzednio z tym ziarnem
    python check_images.py --dir ../scraper-results/przyklady   # wszystkie pliki z katalogu

Kod wyjścia 1 oznacza, że któreś zdjęcie łamie limity (brak pliku, nie JPEG, > 1600 px, > 300 KB).
"""

import argparse
import json
import random
import sys
from pathlib import Path

import config
from PIL import Image, UnidentifiedImageError


def check_file(path, max_side=config.IMAGE_MAX_SIDE_PX, max_bytes=config.IMAGE_MAX_BYTES,
               min_side=config.IMAGE_MIN_SIDE_PX):
    result = {"size": None, "bytes": None, "errors": [], "notes": []}

    if not path.is_file():
        result["errors"].append("brak pliku")
        return result

    result["bytes"] = path.stat().st_size
    try:
        with Image.open(path) as img:
            result["size"] = img.size
            image_format = img.format
    except (UnidentifiedImageError, OSError) as e:
        result["errors"].append(f"nie da się otworzyć: {e}")
        return result

    longer_side = max(result["size"])
    if image_format != "JPEG":
        result["errors"].append(f"format {image_format}, a nie JPEG")
    if longer_side > max_side:
        result["errors"].append(f"dłuższy bok {longer_side} px > {max_side} px")
    if result["bytes"] > max_bytes:
        result["errors"].append(f"{result['bytes']} B > {max_bytes} B")
    if longer_side < min_side:
        result["notes"].append(f"małe: dłuższy bok < {min_side} px")

    return result


def format_row(label, file_name, result):
    size = "{}x{}".format(*result["size"]) if result["size"] else "-"
    kb = f"{result['bytes'] / 1024:.1f}" if result["bytes"] is not None else "-"
    status = "; ".join(result["errors"]) or "OK"
    if result["notes"]:
        status += " (" + "; ".join(result["notes"]) + ")"
    return f"{label:>8}  {file_name:<22} {size:>11} {kb:>9}  {status}"


def sample_products(results_path, count, seed):
    with open(results_path, encoding="utf-8") as file:
        products = json.load(file)
    return random.Random(seed).sample(products, min(count, len(products)))


def collect_from_products(products, results_dir):
    """Lista (etykieta, ścieżka) dla każdego zdjęcia wylosowanych produktów; produkt bez zdjęć to błąd."""
    entries, problems = [], []
    for product in products:
        files = product.get("image_files", [])
        if not files:
            problems.append(f"produkt {product['id']}: brak pobranych zdjęć (uruchom download_images.py)")
        elif len(files) != len(product["image_urls"]):
            print(f"Uwaga: produkt {product['id']} ma {len(files)} z {len(product['image_urls'])} zdjęć")
        entries.extend((str(product["id"]), results_dir / name) for name in files)
    return entries, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=20, help="liczba losowanych produktów (domyślnie 20)")
    parser.add_argument("--seed", type=int, help="ziarno losowania; bez niego losowanie jest za każdym razem inne")
    parser.add_argument("--results", type=Path, default=config.SAVE_PRODUCTS_PATH, help="plik results.json")
    parser.add_argument("--dir", type=Path, help="sprawdź wszystkie *.jpg w katalogu zamiast losować produkty")
    args = parser.parse_args(argv)

    if args.dir:
        entries = [("-", path) for path in sorted(args.dir.glob("*.jpg"))]
        problems = [] if entries else [f"brak plików *.jpg w {args.dir}"]
        print(f"Katalog {args.dir}: {len(entries)} plików")
    else:
        seed = args.seed if args.seed is not None else random.randrange(1_000_000)
        products = sample_products(args.results, args.count, seed)
        entries, problems = collect_from_products(products, args.results.parent)
        print(f"Wylosowano {len(products)} produktów, ziarno {seed} (powtórzenie: --seed {seed})")

    # Tylko znaki z cp1250: konsola Windows nie wypisze "≤" i skrypt by się wywalił
    print(f"Limity: dłuższy bok <= {config.IMAGE_MAX_SIDE_PX} px, plik <= {config.IMAGE_MAX_BYTES} B; KB = 1024 B\n")
    print(f"{'Produkt':>8}  {'Plik':<22} {'Wymiary px':>11} {'KB':>9}  Wynik")

    errors, small, checked = 0, 0, []
    for label, path in entries:
        result = check_file(path)
        print(format_row(label, path.name, result))
        errors += bool(result["errors"])
        small += bool(result["notes"])
        if result["size"]:
            checked.append(result)

    for problem in problems:
        print(f"BŁĄD: {problem}")
    errors += len(problems)

    if checked:
        largest = max(checked, key=lambda r: max(r["size"]))
        heaviest = max(r["bytes"] for r in checked)
        print(
            f"\nSprawdzono {len(entries)} plików. Najdłuższy bok: {max(largest['size'])} px, "
            f"największy plik: {heaviest / 1024:.1f} KB ({heaviest} B), małych zdjęć: {small}"
        )
    print("Wynik: OK" if errors == 0 else f"Wynik: {errors} błędów")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
