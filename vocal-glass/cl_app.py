import base64
from io import BytesIO
from typing import List

import chainlit as cl
from assistants.chains import build_vision_chat_chain
from assistants.llms import get_llm
from assistants.sys_prompts import DEFAULT
from chainlit.element import ElementBased
from loguru import logger
from PIL import Image
from voice_server_clients import call_stt, call_tts

INSTRUCTION = """上传一张图片，我会用声音告诉你图片上的内容
"""


@cl.on_chat_start
async def start():
    await cl.Message(content=INSTRUCTION).send()


def encode_image(img_path: str):
    with open(img_path, "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    return img_base64


def resize_image(image_path: str, max_size=512):

    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size))
        img.save(image_path, quality=85)  # Save with reduced quality if necessary


async def process_images(elements: List[ElementBased]) -> List[str]:
    imgs_base64 = []
    for element in elements:
        if "image" in element.mime:
            resize_image(element.path)
            imgs_base64.append(encode_image(element.path))
    return imgs_base64


async def handle_user_input(
    user_input: str,
    imgs_base64: List[str],
    session_id: str,
):
    chain = build_vision_chat_chain(get_llm(), DEFAULT, imgs_base64)
    inp = {"user_input": user_input}
    msg = cl.Message(content="")
    ai_content = ""
    async for chunk in chain.astream(
        inp, config={"configurable": {"session_id": session_id}}
    ):
        if chunk:
            await msg.stream_token(chunk)
            ai_content += chunk
    await msg.update()
    actions = [
        cl.Action(
            name="生成音频",
            value=ai_content,
            description="点击将AI的回复生成音频",
        )
    ]
    await cl.Message(content="", actions=actions).send()


@cl.on_message
async def chat(message: cl.Message):
    session_id = cl.user_session.get("id")
    images = [file for file in message.elements if "image" in file.mime]
    imgs_base64 = await process_images(images)
    await handle_user_input(message.content, imgs_base64, session_id)


@cl.action_callback("生成音频")
async def generate_audio(action: cl.Action):
    msg = await cl.Message(content="").send()
    audio_url = await call_tts(action.value)
    audio = cl.Audio(url=audio_url, auto_play=True)
    msg.elements = [audio]
    await action.remove()
    await msg.update()


@cl.on_audio_chunk
async def audio_input(chunk: cl.AudioChunk):
    if chunk.isStart:
        buffer = BytesIO()
        cl.user_session.set("audio_buffer", buffer)

    cl.user_session.get("audio_buffer").write(chunk.data)
    logger.debug(f"Audio chunk with size {len(chunk.data)} bytes received")


@cl.on_audio_end
async def on_audio_end(elements: list[ElementBased]):

    # Get the audio buffer from the session
    audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
    user_input = "描述提供的图片"
    if audio_buffer:
        audio_buffer.seek(0)
        transcription = await call_stt(audio_buffer)
        if transcription:
            user_input = transcription
    await cl.Message(
        author="You",
        type="user_message",
        content=user_input,
        elements=elements,
    ).send()

    session_id = cl.user_session.get("id")
    imgs_base64 = await process_images(elements)
    await handle_user_input(user_input, imgs_base64, session_id)
