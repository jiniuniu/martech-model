from functools import lru_cache

from config import env_settings
from f5_tts.api import F5TTS
from faster_whisper import WhisperModel
from loguru import logger


@lru_cache(1)
def load_f5_tts_model():

    f5tts = F5TTS(ckpt_file=env_settings.F5_TTS_CKPT_PATH)
    logger.info("f5 tts loaded.")
    return f5tts


@lru_cache(1)
def load_whisper_model():
    whisper_model = WhisperModel(
        env_settings.WHISPER_MODEL_PATH,
        device="cuda",
        compute_type="float16",
    )
    logger.info("whisper model loaded.")
    return whisper_model
