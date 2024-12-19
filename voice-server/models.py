from functools import lru_cache
from io import BytesIO

import torch
from config import env_settings
from diffusers import (
    BitsAndBytesConfig,
    SD3Transformer2DModel,
    StableDiffusion3Pipeline,
)
from f5_tts.api import F5TTS
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from faster_whisper import WhisperModel
from loguru import logger
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer


@lru_cache(1)
def load_f5_tts_model():

    f5tts = F5TTS(ckpt_file=env_settings.f5_model_path)
    logger.info("f5 tts loaded.")
    return f5tts


@lru_cache(1)
def load_whisper_model():
    whisper_model = WhisperModel(
        env_settings.whisper_model_path,
        device="cuda",
        compute_type="float16",
    )
    logger.info("whisper model loaded.")
    return whisper_model


@lru_cache(1)
def load_sd35_model():
    nf4_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model_nf4 = SD3Transformer2DModel.from_pretrained(
        env_settings.sd35_model_path,
        subfolder="transformer",
        quantization_config=nf4_config,
        torch_dtype=torch.bfloat16,
    )

    pipeline = StableDiffusion3Pipeline.from_pretrained(
        env_settings.sd35_model_path,
        transformer=model_nf4,
        torch_dtype=torch.bfloat16,
    )
    pipeline.enable_model_cpu_offload()
    logger.info("sd35 loaded")
    return pipeline
