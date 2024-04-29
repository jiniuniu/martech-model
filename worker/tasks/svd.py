import math
from functools import lru_cache

import torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import export_to_video, load_image
from loguru import logger
from PIL import Image, UnidentifiedImageError

from common.config import env_settings


@lru_cache(1)
def load_pipe():
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        env_settings.SVD_MODEL_DIR,
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.enable_model_cpu_offload()
    return pipe


def generate_video_from_img(
    image_path: str,
    output_path: str,
    motion_bucket_id: int = 32,
    noise_aug_strength: int = 0.02,
    rounds: int = 2,
) -> str:
    pipe = load_pipe()
    try:
        image = load_image(image_path)
        w, h = image.size
        aspect_ratio = h / w
        image = image.resize((1024, 576), Image.Resampling.LANCZOS)
        imgs: list[Image.Image] = []
        width = 1024
        height = math.floor(width * aspect_ratio)

        for _ in range(rounds):
            frames = pipe(
                image,
                decode_chunk_size=8,
                motion_bucket_id=motion_bucket_id,
                noise_aug_strength=noise_aug_strength,
            ).frames[0]
            imgs += frames
            image = frames[-1]
        imgs = [img.resize((width, height), Image.Resampling.LANCZOS) for img in imgs]
        export_to_video(imgs, output_path, fps=6)
        logger.info(f"Video generated: {output_path}")
        return True
    except UnidentifiedImageError as e:
        logger.error("Image file could not be identified.", exc_info=True)
    except IOError as e:
        logger.error("An I/O error occurred while processing the image.", exc_info=True)
    except Exception as e:
        logger.error("An unexpected error occurred.", exc_info=True)

    return False
