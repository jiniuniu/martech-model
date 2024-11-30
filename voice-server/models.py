from functools import lru_cache

from config import env_settings
from f5_tts.api import F5TTS
from faster_whisper import WhisperModel
from loguru import logger
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
def load_got_ocr_model():
    tokenizer = AutoTokenizer.from_pretrained(
        env_settings.got_ocr_model_path, trust_remote_code=True
    )
    model = AutoModel.from_pretrained(
        env_settings.got_ocr_model_path,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        device_map="cuda",
        use_safetensors=True,
        pad_token_id=tokenizer.eos_token_id,
    )
    model = model.eval().cuda()
    return model, tokenizer
