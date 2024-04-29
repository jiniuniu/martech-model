import io
import os

from fastapi import HTTPException, UploadFile
from PIL import Image

from common.config import env_settings

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def verify_image(image_data: io.BytesIO) -> io.BytesIO:
    """Verify image and return the open stream."""
    try:
        # Open the image to verify it's valid
        image_data.seek(0)  # Ensure the stream's pointer is at the start
        with Image.open(image_data) as image:
            image.verify()  # Verify the image without loading it
        image_data.seek(0)  # Reset the stream's pointer after verification
    except (IOError, SyntaxError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    return image_data  # Return the reset stream


def save_image(filename: str, image_data: io.BytesIO) -> str:
    """Save the image data to a file."""
    out_dir = os.path.join(env_settings.DATA_DIR, "svd_materials")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    img_path = os.path.join(out_dir, filename)
    with open(img_path, "wb") as f:
        f.write(image_data.getvalue())  # Write the image data to file
    return img_path


def validate_image_file(upload_file: UploadFile) -> str:
    extension = upload_file.filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported MIME type.")
    upload_file.file.seek(0)
    image_data = io.BytesIO(upload_file.file.read())
    verified_image = verify_image(image_data)
    return save_image(upload_file.filename, verified_image)
