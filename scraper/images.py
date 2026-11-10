import io
import logging
import os
from collections import Counter
from dataclasses import dataclass

import config
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

START_QUALITY = 90
MIN_QUALITY = 20
QUALITY_STEP = 5
# Gdy nawet MIN_QUALITY daje za duży plik, obraz jest zmniejszany o 10% i pętla jakości startuje od nowa
SHRINK_FACTOR = 0.9


@dataclass
class ResizedImage:
    data: bytes
    original_size: tuple[int, int]
    size: tuple[int, int]
    quality: int


def to_rgb(img):
    """JPEG nie ma kanału alfa, więc przezroczystość zamieniamy na białe tło (jak w sklepie)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")


def encode_jpeg(img, quality):
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def resize_image(data, max_side=config.IMAGE_MAX_SIDE_PX, max_bytes=config.IMAGE_MAX_BYTES):
    """Zmniejsza obraz tak, by dłuższy bok miał ≤ max_side, i zapisuje JPEG ≤ max_bytes.

    Mniejsze obrazy nie są powiększane. Jakość spada od START_QUALITY co QUALITY_STEP,
    aż plik zmieści się w limicie.
    """
    with Image.open(io.BytesIO(data)) as source:
        original_size = source.size
        img = to_rgb(ImageOps.exif_transpose(source))

    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    while True:
        for quality in range(START_QUALITY, MIN_QUALITY - 1, -QUALITY_STEP):
            encoded = encode_jpeg(img, quality)
            if len(encoded) <= max_bytes:
                return ResizedImage(encoded, original_size, img.size, quality)

        smaller = (max(1, round(img.width * SHRINK_FACTOR)), max(1, round(img.height * SHRINK_FACTOR)))
        logger.warning("Jakość %d to za mało dla %dx%d, zmniejszam do %dx%d", MIN_QUALITY, *img.size, *smaller)
        img = img.resize(smaller, Image.Resampling.LANCZOS)


def image_filename(product_id, index):
    return f"{product_id}-{index}.jpg"


def write_atomic(path, data):
    """Przerwany zapis nie zostawia uciętego pliku, który następne uruchomienie uznałoby za pobrany."""
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, path)


class ImageDownloader:
    def __init__(self, client, images_dir, min_side=config.IMAGE_MIN_SIDE_PX):
        self.client = client
        self.images_dir = images_dir
        self.min_side = min_side
        self.stats = Counter()

    def log_if_small(self, product_id, url, size):
        if max(size) < self.min_side:
            self.stats["małe"] += 1
            logger.warning(
                "Małe zdjęcie produktu %s: %dx%d, dłuższy bok < %d px (%s)", product_id, *size, self.min_side, url
            )

    def download(self, product_id, image_urls):
        """Zwraca nazwy plików w images_dir w kolejności image_urls; nieudane zdjęcia są pomijane."""
        files = []

        for index, url in enumerate(image_urls, 1):
            url = str(url)
            path = self.images_dir / image_filename(product_id, index)

            if path.exists():
                self.stats["pominięte"] += 1
                with Image.open(path) as saved:
                    self.log_if_small(product_id, url, saved.size)
                files.append(path.name)
                continue

            response = self.client.get(url)
            if response is None:
                self.stats["błędy"] += 1
                continue

            try:
                resized = resize_image(response.content)
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
                self.stats["błędy"] += 1
                logger.warning("Nie udało się odczytać zdjęcia %s: %s", url, e)
                continue

            write_atomic(path, resized.data)
            self.stats["pobrane"] += 1
            self.log_if_small(product_id, url, resized.original_size)
            logger.info(
                "Zapisano %s: %dx%d -> %dx%d, jakość %d, %.1f KB",
                path.name,
                *resized.original_size,
                *resized.size,
                resized.quality,
                len(resized.data) / 1024,
            )
            files.append(path.name)

        return files
