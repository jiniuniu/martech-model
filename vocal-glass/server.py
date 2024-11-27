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
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from storage_conn.qiniu_conn import get_qiniu
from ws_conn import ConnectionManager

conn_mgr = ConnectionManager()
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
        with open(file_path, "wb") as f:
            f.write(buffer.read())
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


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    session_id = await conn_mgr.connect(websocket)
    try:
        while True:
            message = websocket.receive()

            if isinstance(message, bytes):  # Audio data
                logger.debug(f"audio data received, size: {len(message)} bytes")
                connection_info = conn_mgr.active_connections[websocket]
                connection_info["audio_buffer"].write(message)
            elif isinstance(message, str):
                if message == "pong":
                    logger.debug(f"Pong received for session_id: {session_id}")
                elif message == "stop_recording":
                    logger.info("Stop recording received, processing audio.")
                    await process_audio_and_respond(websocket, session_id)
                else:
                    logger.info(f"Text message received: {message}")

    except WebSocketDisconnect:
        logger.warning("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"Error in WebSocket communication: {e}")
    finally:
        await conn_mgr.disconnect(websocket)


async def process_audio_and_respond(websocket: WebSocket, session_id: str):
    """Processes the audio buffer, generates responses, and sends them back."""
    connection_info = conn_mgr.active_connections[websocket]
    audio_buffer: BytesIO = connection_info["audio_buffer"]

    # Reset the buffer to read from the beginning
    audio_buffer.seek(0)

    # Transcribe the audio
    transcription = transcribe_audio(audio_buffer)
    logger.info(f"Transcribed text: {transcription}")

    # Send transcription to the client
    await websocket.send_json({"type": "transcription", "content": transcription})

    # Generate chat response and send TTS audio interleave
    await generate_response(transcription, session_id)

    # Clear the buffer for the next recording
    audio_buffer.seek(0)
    audio_buffer.truncate(0)


async def generate_response(websocket: WebSocket, session_id: str, text: str):
    inp = {"prompt": text}
    complete_text = ""
    accumulated_text = ""
    chat_chain = build_vision_chat_chain(get_llm(), DEFAULT)
    async for chunk in chat_chain.astream(
        inp, config={"configurable": {"session_id": session_id}}
    ):
        if chunk:
            complete_text += chunk
            accumulated_text += chunk
            await websocket.send_json({"type": "response_text", "content": chunk})
            if chunk.endswith("\n"):
                if accumulated_text.strip() == "":
                    continue
                logger.debug(f"accumulated text: {accumulated_text}")
                await generate_and_send_tts(websocket, accumulated_text)
                accumulated_text = ""

    # Send any remaining text
    if accumulated_text:
        logger.debug(f"Remaining text: {accumulated_text}")
        await generate_and_send_tts(websocket, accumulated_text)

    logger.debug(f"complete text: {complete_text}")


async def generate_and_send_tts(websocket: WebSocket, text: str):
    try:
        # Generate PCM data
        pcm_buffer = text_to_speech(text)
        pcm_data = pcm_buffer.read()

        # Prepare WAV file parameters
        channels = 1  # mono
        sample_width = 2  # 16-bit
        sample_rate = 16000

        # Create a WAV header
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)

        # Get the complete WAV file data
        wav_data = wav_buffer.getvalue()

        # Send WAV file in small chunks
        chunk_size = 1024  # Adjust as needed
        for i in range(0, len(wav_data), chunk_size):
            chunk = wav_data[i : i + chunk_size]
            await websocket.send_bytes(chunk)

        # Optional: Send a final marker to indicate end of audio
        await websocket.send_json({"type": "audio_end"})

    except Exception as e:
        logger.exception(f"Failed to generate or send TTS data. {e}")
        await websocket.close(code=1011, reason="Internal server error")


mount_chainlit(app=app, target="cl_app.py", path="/chatui")
