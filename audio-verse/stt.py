import time
from io import BytesIO

from load_models import load_whisper_model
from loguru import logger


def transcribe_audio(buffer: BytesIO) -> str:
    try:
        whisper_model = load_whisper_model()
        start = time.time()
        segs, _ = whisper_model.transcribe(buffer, beam_size=5)
        tot = time.time() - start
        logger.debug(f"Transcription time: {tot:.2f} seconds")
        res = " ".join([seg.text for seg in segs])
        return res
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "there is something wrong with the transcription."
