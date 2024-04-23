import io
import os
import shutil

from fastapi import HTTPException, UploadFile
from PIL import Image

from svd_service.config import env_settings


def validate_image_file(upload_file: UploadFile):
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    allowed_mime_types = {"image/jpeg", "image/png", "image/webp"}

    # Validate file extension
    extension = upload_file.filename.split(".")[-1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")

    # Validate MIME type
    if upload_file.content_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Unsupported MIME type.")

    # Validate and save the image file
    try:
        # Reset file pointer and read the content
        upload_file.file.seek(0)
        image_data = io.BytesIO(upload_file.file.read())
        image = Image.open(image_data)
        image.verify()  # Verify the image

        # Reset and read again for saving, since verify() can destroy the stream
        upload_file.file.seek(0)
        # Define the full path for the image
        out_dir = os.path.join(env_settings.DATA_DIR, "svd_materials")
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        img_path = os.path.join(out_dir, upload_file.filename)
        with open(img_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
    except (IOError, SyntaxError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    return img_path
