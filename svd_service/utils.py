import io
import os

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image

from svd_service.config import env_settings

allowed_extensions = {"jpg", "jpeg", "png", "webp"}
allowed_mime_types = {"image/jpeg", "image/png", "image/webp"}


async def download_and_verify_image(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Could not retrieve image from URL."
            )
        content_type = response.headers["Content-Type"].lower()
        if content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=400, detail="Unsupported MIME type from URL."
            )

        image_data = io.BytesIO(response.content)
        return verify_image(image_data)


def verify_image(image_data: io.BytesIO):
    try:
        image = Image.open(image_data)
        image.verify()  # Verify that it's a real image
        image_data.seek(0)
        image = Image.open(image_data)  # Reopen for further use
        image.close()
    except (IOError, SyntaxError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    return image_data


async def validate_image_file(upload_file: UploadFile = None, image_url: str = None):

    if upload_file and image_url:
        raise HTTPException(
            status_code=400,
            detail="Please provide either an upload file or an image URL, not both.",
        )

    if upload_file:
        extension = upload_file.filename.split(".")[-1].lower()
        if extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Unsupported file extension.")
        if upload_file.content_type not in allowed_mime_types:
            raise HTTPException(status_code=400, detail="Unsupported MIME type.")
        upload_file.file.seek(0)
        image_data = io.BytesIO(upload_file.file.read())
        verified_image = verify_image(image_data)
        return save_image(upload_file.filename, verified_image)

    elif image_url:
        image_data = await download_and_verify_image(image_url)
        filename = os.path.basename(image_url)
        return save_image(filename, image_data)
    else:
        raise HTTPException(status_code=400, detail="No image provided.")


def save_image(filename, image_data):
    out_dir = os.path.join(env_settings.DATA_DIR, "frames")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    img_path = os.path.join(out_dir, filename)
    with open(img_path, "wb") as f:
        f.write(image_data.getvalue())
    return img_path
