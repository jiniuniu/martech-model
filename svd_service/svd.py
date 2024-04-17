from functools import lru_cache

import torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import export_to_video
from loguru import logger
from PIL import Image

from common.config import env_settings
from common.qiniu_conn import get_qiniu

UPLOAD_PREFIX = "svd_materials"


@lru_cache(1)
def load_pipe():
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        env_settings.SVD_MODEL_DIR,
        torch_dtype=torch.float16,
        variant="fp16",
    )
    return pipe


def generate_video_from_img(
    image_path: str,
    output_path: str,
    motion_bucket_id: int = 127,
    noise_aug_strength: int = 0.02,
    upload: bool = True,
) -> str:
    pipe = load_pipe()
    pipe.to("cuda")
    try:
        image = Image.open(image_path)
        image = image.convert("RGB").resize((1024, 576))
        frames = pipe(
            image,
            decode_chunk_size=8,
            motion_bucket_id=motion_bucket_id,
            noise_aug_strength=noise_aug_strength,
        ).frames[0]
        export_to_video(frames, output_path, fps=7)
        logger.info(f"Video generated: {output_path}")
        if upload:
            qiniu = get_qiniu()
            upload_key = qiniu.upload_file(
                output_path,
                upload_dir=UPLOAD_PREFIX,
            )
            video_url = qiniu.get_public_url(upload_key)
            logger.info(f"uploaded video url: {video_url}")
            return video_url
        else:
            return output_path
    except Exception as e:
        logger.error(f"Error in video generation: {e}")
        return ""
