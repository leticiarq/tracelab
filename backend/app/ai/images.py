import hashlib
import io

from PIL import Image, UnidentifiedImageError

from app.ai.errors import AIImageError
from app.ai.models import PreparedImage

SUPPORTED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def prepare_images(
    inputs: list[tuple[bytes, str | None]],
    *,
    max_images: int,
    max_bytes: int,
    max_dimension: int,
) -> list[PreparedImage]:
    if len(inputs) > max_images:
        raise AIImageError(f"Envie no máximo {max_images} imagens por operação.")
    prepared: list[PreparedImage] = []
    seen: set[str] = set()
    for content, _media_type in inputs:
        if not content:
            raise AIImageError("Uma das imagens enviadas está vazia.")
        if len(content) > max_bytes:
            raise AIImageError(f"Cada imagem deve ter no máximo {max_bytes // (1024 * 1024)} MB.")
        digest = hashlib.sha256(content).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        prepared.append(_resize_image(content, digest, max_dimension))
    if not prepared:
        raise AIImageError("Envie ao menos uma imagem válida e não duplicada.")
    return prepared


def _resize_image(content: bytes, digest: str, max_dimension: int) -> PreparedImage:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image_format = image.format
            if image_format not in SUPPORTED_FORMATS:
                raise AIImageError("Use imagens PNG, JPEG ou WebP.")
            image.load()
            if max(image.size) <= max_dimension:
                return PreparedImage(content, SUPPORTED_FORMATS[image_format], digest)
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            if image_format == "JPEG":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                image.save(output, format="JPEG", quality=88, optimize=True)
            else:
                image.save(output, format=image_format, optimize=True)
            resized = output.getvalue()
            return PreparedImage(resized, SUPPORTED_FORMATS[image_format], hashlib.sha256(resized).hexdigest())
    except (UnidentifiedImageError, OSError) as exc:
        raise AIImageError("Não foi possível ler uma das imagens enviadas.") from exc
