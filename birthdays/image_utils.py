from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image


def compress_image_file(image_field, max_size=(512, 512), quality=82):
    img = Image.open(image_field)
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)

    base_name = image_field.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return InMemoryUploadedFile(
        buffer,
        "ImageField",
        f"{base_name}.jpg",
        "image/jpeg",
        buffer.getbuffer().nbytes,
        None,
    )
