import base64
import os
import wave
from io import BytesIO
from typing import List

import shortuuid
from assistants.chains import build_vision_chat_chain
from assistants.llms import get_llm
from assistants.sys_prompts import DEFAULT
from audio.api import text_to_speech, transcribe_audio
from chainlit.utils import mount_chainlit
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from storage_conn.qiniu_conn import get_qiniu

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
        file_name = shortuuid.ShortUUID().random(length=11)
        file_path = f"/tmp/{file_name}.wav"
        q = get_qiniu()
        file_key = q.upload_file(file_path, "audio_assets")
        audio_url = q.get_public_url(file_key)
        os.remove(file_path)
        # Return the base64-encoded audio in a JSON response
        return {"audio_url": audio_url}
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


class VisionRequest(BaseModel):
    user_input: str
    session_id: str
    images_base64: List[str] = []


@app.post("/vision_chat")
async def vision_chat(request: VisionRequest):
    try:
        user_input = request.user_input
        session_id = request.session_id
        images_base64 = request.images_base64
        vision_chain = build_vision_chat_chain(get_llm(), DEFAULT, images_base64)

        inp = {"user_input": user_input}

        async def generate():
            msg = ""
            async for chunk in vision_chain.astream(
                inp, config={"configurable": {"session_id": session_id}}
            ):
                if chunk:
                    msg += chunk
                    yield chunk

        return StreamingResponse(generate(), media_type="text/plain")
    except Exception as e:
        # Log the exception for further analysis
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


mount_chainlit(app=app, target="cl_app.py", path="/chatui")
