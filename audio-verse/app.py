import base64
import wave
from io import BytesIO

from chains import build_chat_chain
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from prompts import CHAT_SYS_MSG
from pydantic import BaseModel
from stt import transcribe_audio
from tts import text_to_speech
from ws_manager import ConnectionManager

chat_chain = build_chat_chain(CHAT_SYS_MSG)

ws_conn_manager = ConnectionManager()
app = FastAPI()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    session_id = await ws_conn_manager.connect(websocket)
    try:
        while True:
            message = websocket.receive()

            if isinstance(message, bytes):  # Audio data
                logger.debug(f"audio data received, size: {len(message)} bytes")
                connection_info = ws_conn_manager.active_connections[websocket]
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
        await ws_conn_manager.disconnect(websocket)


async def process_audio_and_respond(websocket: WebSocket, session_id: str):
    """Processes the audio buffer, generates responses, and sends them back."""
    connection_info = ws_conn_manager.active_connections[websocket]
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
        # Call the text_to_speech function to generate PCM data
        pcm_buffer = text_to_speech(text)

        # Read the PCM data from the buffer
        pcm_data = pcm_buffer.read()
        # Send PCM data in smaller chunks
        chunk_size = 1024  # Adjust chunk size as needed
        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i : i + chunk_size]
            await websocket.send_bytes(chunk)

    except Exception as e:
        # Handle and log errors
        logger.exception(f"Failed to generate or send TTS data. {e}")
        await websocket.close(code=1011, reason="Internal server error")


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
