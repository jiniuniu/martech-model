import re
import time
from importlib.resources import files
from io import BytesIO

import librosa
import numpy as np
from audio.models import load_f5_tts_model, load_whisper_model
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


def text_to_speech(text: str) -> BytesIO:
    try:
        f5tts = load_f5_tts_model()
        text = text.strip()
        text = re.sub(r"~+", "!", text)
        text = re.sub(r"\(.*?\)", "", text)
        text = re.sub(r"(\*[^*]+\*)|(_[^_]+_)", "", text).strip()
        text = re.sub(r"[^\x00-\x7F]+", "", text)
        t0 = time.time()
        wav_np, sr, _ = f5tts.infer(
            ref_file=str(
                files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav")
            ),
            ref_text="some call me nature, others call me mother nature.",
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

        # Convert PCM to 16-bit integer format for streaming
        wav_int16 = (wav_np_24k * 32767).astype(np.int16)

        # Prepare PCM data for streaming
        buffer = BytesIO(wav_int16.tobytes())
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise