import base64

from assistants.chains import build_vision_chat_chain
from assistants.llms import get_llm
from assistants.sys_prompts import DEFAULT_2
from chainlit.utils import mount_chainlit
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request
from voice_server_clients import call_stt, call_tts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# Static files and templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/ui", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit")
async def process_data(
    session_id: str = Form(...),
    photo: UploadFile = File(...),
    audio: UploadFile = File(None),
):
    photo_content = await photo.read()
    img_base64 = base64.b64encode(photo_content).decode("utf-8")
    audio_content = await audio.read() if audio else None
    user_input = "帮我描述这张图片"
    if audio_content:
        transcription = await call_stt(audio_content)
        if transcription:
            user_input = transcription
            logger.info(f"user: {user_input}")
    chain = build_vision_chat_chain(get_llm(), DEFAULT_2, images_base64=[img_base64])
    inp = {"user_input": user_input}

    # async for chunk in chain.astream(
    #     inp, config={"configurable": {"session_id": session_id}}
    # ):
    #     if chunk:
    #         await msg.stream_token(chunk)
    #         ai_content += chunk
    response_text = await chain.ainvoke(
        inp, config={"configurable": {"session_id": session_id}}
    )
    logger.info(f"response: {response_text}")
    audio_url = await call_tts(response_text) or ""
    return JSONResponse(content={"text": response_text, "audio_url": audio_url})


mount_chainlit(app, "cl_app.py", "/chatui")
