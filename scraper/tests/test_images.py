"""Przeskalowanie i pobieranie zdjęć na obrazach generowanych w teście, bez internetu."""

import io
import random

import pytest
from check_images import check_file
from conftest import FakeClient
from images import START_QUALITY, ImageDownloader, resize_image
from PIL import Image

MAX_SIDE = 1600
MAX_BYTES = 300_000


def noisy_photo(width, height, seed=0):
    """Gradient z szumem: kompresuje się jak zdjęcie, więc przy jakości 90 przekracza 300 KB."""
    gradient = Image.linear_gradient("L").resize((width, height))
    noise = Image.frombytes("L", (width, height), random.Random(seed).randbytes(width * height))
    return Image.merge("RGB", (gradient, noise, Image.blend(gradient, noise, 0.5)))


def to_bytes(img, image_format="JPEG", **params):
    buffer = io.BytesIO()
    img.save(buffer, image_format, **params)
    return buffer.getvalue()


def open_result(resized):
    img = Image.open(io.BytesIO(resized.data))
    img.load()
    return img


def test_large_image_is_scaled_and_compressed():
    original = to_bytes(noisy_photo(4000, 2500), quality=95)
    assert len(original) > MAX_BYTES

    resized = resize_image(original)
    img = open_result(resized)

    assert img.format == "JPEG"
    assert img.size == resized.size == (1600, 1000)  # proporcje 8:5 zachowane
    assert resized.original_size == (4000, 2500)
    assert len(resized.data) <= MAX_BYTES
    assert resized.quality < START_QUALITY  # limit wymusił obniżenie jakości


def test_portrait_image_longer_side_is_height():
    resized = resize_image(to_bytes(noisy_photo(1200, 3000)))
    assert resized.size == (640, 1600)


def test_incompressible_image_still_fits_limit():
    """Czysty szum nie mieści się w 300 KB nawet przy najniższej jakości, więc obraz jest dodatkowo zmniejszany."""
    noise = Image.frombytes("RGB", (1600, 1600), random.Random(1).randbytes(1600 * 1600 * 3))
    resized = resize_image(to_bytes(noise, "PNG"))

    assert len(resized.data) <= MAX_BYTES
    assert max(resized.size) < MAX_SIDE


def test_small_image_is_not_upscaled():
    resized = resize_image(to_bytes(noisy_photo(600, 400)))
    assert resized.size == (600, 400)
    assert resized.quality == START_QUALITY


def test_transparent_png_gets_white_background():
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
    resized = resize_image(to_bytes(img, "PNG"))
    result = open_result(resized)

    assert result.mode == "RGB"
    assert all(channel > 245 for channel in result.getpixel((50, 50)))


LARGE_URL = "https://gitara-sklep.pl/1/duze.jpg"
SMALL_URL = "https://gitara-sklep.pl/2/male.jpg"
HTML_URL = "https://gitara-sklep.pl/3/strona-bledu.jpg"
MISSING_URL = "https://gitara-sklep.pl/4/404.jpg"


@pytest.fixture
def responses():
    return {
        LARGE_URL: to_bytes(noisy_photo(2400, 1800)),
        SMALL_URL: to_bytes(noisy_photo(700, 500)),
        HTML_URL: b"<html>Not found</html>",
    }


def test_downloader_names_files_and_logs_small_images(tmp_path, responses, caplog):
    downloader = ImageDownloader(FakeClient(responses), tmp_path)

    files = downloader.download(487, [LARGE_URL, SMALL_URL, HTML_URL, MISSING_URL])

    # Numer w nazwie to pozycja w image_urls, więc nieudane zdjęcie nie przesuwa kolejnych
    assert files == ["487-1.jpg", "487-2.jpg"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["487-1.jpg", "487-2.jpg"]
    small_warnings = [record.getMessage() for record in caplog.records if "Małe zdjęcie" in record.getMessage()]
    assert small_warnings == [f"Małe zdjęcie produktu 487: 700x500, dłuższy bok < 800 px ({SMALL_URL})"]
    assert f"Nie udało się odczytać zdjęcia {HTML_URL}" in caplog.text
    assert downloader.stats == {"pobrane": 2, "błędy": 2, "małe": 1}
    for path in tmp_path.iterdir():
        assert check_file(path, MAX_SIDE, MAX_BYTES)["errors"] == []


def test_downloader_skips_already_downloaded(tmp_path, responses, caplog):
    ImageDownloader(FakeClient(responses), tmp_path).download(487, [LARGE_URL, SMALL_URL])
    first_run = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    caplog.clear()

    client = FakeClient(responses)
    downloader = ImageDownloader(client, tmp_path)
    files = downloader.download(487, [LARGE_URL, SMALL_URL])

    assert client.requested == []
    assert files == ["487-1.jpg", "487-2.jpg"]
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == first_run
    assert downloader.stats == {"pominięte": 2, "małe": 1}
    assert "Małe zdjęcie produktu 487" in caplog.text  # małe zdjęcie trafia do logu także przy pominięciu


def test_check_file_reports_violations(tmp_path):
    too_big = tmp_path / "duze.jpg"
    too_big.write_bytes(to_bytes(noisy_photo(2000, 1000), quality=95))
    png = tmp_path / "obraz.jpg"
    png.write_bytes(to_bytes(Image.new("RGB", (500, 500)), "PNG"))

    errors = check_file(too_big, MAX_SIDE, MAX_BYTES)["errors"]
    assert "dłuższy bok 2000 px > 1600 px" in errors
    assert any("B > 300000 B" in error for error in errors)

    result = check_file(png, MAX_SIDE, MAX_BYTES)
    assert result["errors"] == ["format PNG, a nie JPEG"]
    assert result["notes"] == ["małe: dłuższy bok < 800 px"]
    assert check_file(tmp_path / "brak.jpg")["errors"] == ["brak pliku"]
