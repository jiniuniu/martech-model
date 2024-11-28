import time
from importlib.resources import files
from io import BytesIO

import librosa
import numpy as np
import regex as re
import soundfile as sf
from loguru import logger
from models import load_f5_tts_model, load_whisper_model


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


def text_to_speech(text: str) -> BytesIO:
    try:
        f5tts = load_f5_tts_model()
        text = text.strip()
        # Replace sequences of `~` with `!`
        text = re.sub(r"~+", "!", text)
        # Remove content within parentheses (including parentheses themselves)
        text = re.sub(r"\(.*?\)", "", text)
        # Remove content wrapped in `*` or `_` (e.g., *italic* or _underscore_)
        text = re.sub(r"(\*[^*]+\*)|(_[^_]+_)", "", text).strip()
        # Ensure that English, non-Chinese characters and non-punctuation characters are removed
        text = re.sub(r"[^\x00-\x7F\u4E00-\u9FFF\p{P}]+", "", text)
        t0 = time.time()
        wav_np, sr, _ = f5tts.infer(
            ref_file="voices/nova.wav",
            ref_text="",
            gen_text=text,
        )
        generation_time = time.time() - t0
        audio_duration = len(wav_np) / sr
        rtf = generation_time / audio_duration
        logger.debug(f"Generated in {generation_time:.2f}s")
        logger.debug(f"Real-Time Factor (RTF): {rtf:.2f}")
        wav_np = np.clip(wav_np, -1, 1)

        # Resample to 24kHz
        if sr != 24000:
            wav_np_24k = librosa.resample(wav_np, orig_sr=sr, target_sr=24000)
        else:
            wav_np_24k = wav_np

        # Convert to Opus using an in-memory buffer
        buffer = BytesIO()
        sf.write(buffer, wav_np_24k, 24000, format="ogg", subtype="opus")
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
