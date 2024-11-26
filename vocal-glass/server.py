import base64
import wave
from io import BytesIO

from audio.api import text_to_speech, transcribe_audio
from chainlit.utils import mount_chainlit
from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

app = FastAPI()


class TTSRequest(BaseModel):

    text: str


@app.post("/text_to_wav")
async def text_to_wav(request: TTSRequest):
    try:
        pcm_buffer = text_to_speech(request.text)
        # Convert raw PCM data to WAV format
        pcm_data = pcm_buffer.read()
        buffer = BytesIO()
        target_sr = 24000  # Assuming 24 kHz as the sampling rate

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(target_sr)
            wav_file.writeframes(pcm_data)

        # Reset buffer position
        buffer.seek(0)

        # Base64 encode the WAV file
        encoded_audio = base64.b64encode(buffer.read()).decode("utf-8")

        # Return the base64-encoded audio in a JSON response
        return {"encoded_audio": encoded_audio}
    except Exception as e:
        logger.exception(f"Failed to generate or send TTS data. {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/audio_to_text")
async def audio_to_text(file: UploadFile = File(...)):
    try:
        # Read the file into a BytesIO buffer
        buffer = BytesIO(await file.read())

        # Perform transcription
        transcription = transcribe_audio(buffer)

        # Return the transcription result
        return {"transcription": transcription}

    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")


mount_chainlit(app=app, target="cl_app.py", path="/chatui")
