"""Stage A image preprocessing (spec §8) with the upload checks from §29.

Accepts PNG, JPEG, and WebP identified by content (never by filename), rejects oversized
images before decoding them, applies EXIF orientation, flattens transparency onto white,
and downscales — preserving aspect ratio — only when the longest side exceeds a limit.
Images are never upscaled, so small text is not resized out of existence.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "WEBP"})
MIN_SIDE = 16


class ImageError(ValueError):
    """The input is not an image we accept; the message is safe to show to users."""


@dataclass(frozen=True)
class PreprocessedImage:
    image: Image.Image  # RGB, ready for the VLM
    format: str
    original_size: tuple[int, int]  # after EXIF orientation, before any resize
    sha256: str  # of the original bytes; used for caching (§30) and logging

    @property
    def resized(self) -> bool:
        return self.image.size != self.original_size


def preprocess_image(data: bytes, *, max_side: int, max_pixels: int) -> PreprocessedImage:
    if not data:
        raise ImageError("the file is empty")

    try:
        with Image.open(io.BytesIO(data)) as opened:
            image_format = opened.format or "unknown"
            if image_format not in ALLOWED_FORMATS:
                allowed = ", ".join(sorted(ALLOWED_FORMATS))
                raise ImageError(f"unsupported image format {image_format} (allowed: {allowed})")
            _check_dimensions(*opened.size, max_pixels=max_pixels)
            opened.load()
            image = ImageOps.exif_transpose(opened)
    except ImageError:
        raise
    except Image.DecompressionBombError as exc:
        # Pillow refuses extreme sizes already at open(), before our own check runs.
        raise ImageError(f"image is too large (limit {max_pixels:,} pixels)") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageError("the file is not a readable image") from exc

    original_size = image.size
    image = _fit_within(_to_rgb(image), max_side)
    return PreprocessedImage(
        image=image,
        format=image_format,
        original_size=original_size,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _check_dimensions(width: int, height: int, *, max_pixels: int) -> None:
    if width * height > max_pixels:
        raise ImageError(
            f"image is too large ({width}x{height} = {width * height:,} pixels; "
            f"limit {max_pixels:,})"
        )
    if min(width, height) < MIN_SIDE:
        raise ImageError(f"image is too small ({width}x{height}; minimum side {MIN_SIDE}px)")


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    if image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info:
        # Plain convert("RGB") would drop alpha and often leave a black background.
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        return flattened
    return image.convert("RGB")


def _fit_within(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image
    scale = max_side / longest
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)
