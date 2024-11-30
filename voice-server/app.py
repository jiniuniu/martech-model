import os
import uuid
from io import BytesIO

from api import ocr_image, text_to_speech, transcribe_audio
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
async def tts(request: TTSRequest):
    try:
        audio_buffer = text_to_speech(request.text)
        return StreamingResponse(audio_buffer, media_type="audio/ogg; codecs=opus")

    except Exception as e:
        logger.exception(f"Failed to generate or send TTS data. {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/stt")
async def stt(file: UploadFile = File(...)):
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


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if file.content_type.startswith("image/"):
        # Save the file temporarily
        temp_file_path = f"/tmp/{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
        # Process the image
        ocr_result = ocr_image(temp_file_path)

        # Clean up the temporary file
        os.remove(temp_file_path)
        return {"ocr_result": ocr_result}
    else:
        return {"error": "File is not an image"}
