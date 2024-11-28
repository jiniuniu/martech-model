from api import text_to_speech
from fastapi import FastAPI, HTTPException
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
