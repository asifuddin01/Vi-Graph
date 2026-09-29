import hashlib
import io
import struct
import zlib

import pytest
from PIL import Image

from app.utils.images import ImageError, PreprocessedImage, preprocess_image

LIMITS = {"max_side": 2048, "max_pixels": 40_000_000}


def encode(image: Image.Image, fmt: str = "PNG", **save_kwargs: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def preprocess(data: bytes, **overrides: int) -> PreprocessedImage:
    return preprocess_image(data, **{**LIMITS, **overrides})


# --- accepted inputs ------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_supported_formats_are_accepted(fmt: str) -> None:
    result = preprocess(encode(Image.new("RGB", (320, 200), "white"), fmt))

    assert result.format == fmt
    assert result.image.mode == "RGB"


def test_small_image_is_left_at_original_size() -> None:
    result = preprocess(encode(Image.new("RGB", (640, 480), "white")))

    assert result.image.size == (640, 480)
    assert result.original_size == (640, 480)
    assert not result.resized


def test_large_image_is_downscaled_preserving_aspect_ratio() -> None:
    result = preprocess(encode(Image.new("RGB", (4000, 1000), "white")))

    assert result.image.size == (2048, 512)
    assert result.original_size == (4000, 1000)
    assert result.resized


def test_tall_image_is_bounded_by_its_longest_side() -> None:
    result = preprocess(encode(Image.new("RGB", (999, 3001), "white")), max_side=1000)

    width, height = result.image.size
    assert height == 1000
    assert width == round(999 * 1000 / 3001)


def test_images_are_never_upscaled() -> None:
    result = preprocess(encode(Image.new("RGB", (100, 50), "white")), max_side=1024)

    assert result.image.size == (100, 50)


def test_transparent_background_is_flattened_to_white() -> None:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    image.putpixel((10, 10), (255, 0, 0, 255))

    result = preprocess(encode(image))

    assert result.image.mode == "RGB"
    assert result.image.getpixel((0, 0)) == (255, 255, 255)
    assert result.image.getpixel((10, 10)) == (255, 0, 0)


def test_palette_image_with_transparency_is_flattened_to_white() -> None:
    image = Image.new("P", (64, 64), 0)
    image.putpalette([0, 0, 0, 0, 0, 255] + [0] * (254 * 3))
    image.putpixel((5, 5), 1)

    result = preprocess(encode(image, transparency=0))

    assert result.image.getpixel((0, 0)) == (255, 255, 255)
    assert result.image.getpixel((5, 5)) == (0, 0, 255)


def test_grayscale_is_converted_to_rgb() -> None:
    result = preprocess(encode(Image.new("L", (64, 64), 128)))

    assert result.image.mode == "RGB"
    assert result.image.getpixel((0, 0)) == (128, 128, 128)


def test_exif_orientation_is_applied() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise on display

    result = preprocess(encode(Image.new("RGB", (400, 100), "white"), "JPEG", exif=exif))

    assert result.original_size == (100, 400)
    assert result.image.size == (100, 400)


def test_sha256_is_of_the_original_bytes() -> None:
    data = encode(Image.new("RGB", (64, 64), "white"))

    assert preprocess(data).sha256 == hashlib.sha256(data).hexdigest()


# --- rejected inputs ------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_other_image_formats_are_rejected(fmt: str) -> None:
    with pytest.raises(ImageError, match=f"unsupported image format {fmt}"):
        preprocess(encode(Image.new("RGB", (64, 64), "white"), fmt))


@pytest.mark.parametrize(
    "data",
    [b"not an image", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", b"%PDF-1.7"],
    ids=["text", "svg", "pdf"],
)
def test_non_images_are_rejected(data: bytes) -> None:
    with pytest.raises(ImageError, match="not a readable image"):
        preprocess(data)


def test_empty_file_is_rejected() -> None:
    with pytest.raises(ImageError, match="empty"):
        preprocess(b"")


def test_truncated_image_is_rejected() -> None:
    data = encode(Image.effect_noise((256, 256), 64).convert("RGB"))

    with pytest.raises(ImageError, match="not a readable image"):
        preprocess(data[: len(data) // 2])


def test_too_many_pixels_is_rejected() -> None:
    with pytest.raises(ImageError, match="too large"):
        preprocess(encode(Image.new("RGB", (200, 200), "white")), max_pixels=39_999)


def png_declaring_size(width: int, height: int) -> bytes:
    """A tiny PNG whose header claims the given size but that has no pixel data."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload)
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", b"") + chunk(b"IEND", b"")


@pytest.mark.parametrize(
    ("width", "height"),
    [(10_000, 5_000), (20_000, 20_000)],
    ids=["over-our-limit", "over-pillow-bomb-limit"],
)
def test_decompression_bombs_are_rejected_from_the_header(width: int, height: int) -> None:
    data = png_declaring_size(width, height)
    assert len(data) < 100  # nothing to decode: rejection must come from the header alone

    with pytest.raises(ImageError, match="too large"):
        preprocess(data)


def test_too_small_is_rejected() -> None:
    with pytest.raises(ImageError, match="too small"):
        preprocess(encode(Image.new("RGB", (400, 10), "white")))
