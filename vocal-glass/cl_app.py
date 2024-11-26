from io import BytesIO
from typing import List

import chainlit as cl
from assistants.chains import build_vision_chat_chain
from assistants.llms import get_llm
from assistants.sys_prompts import DEFAULT
from audio.api import transcribe_audio
from chainlit.element import ElementBased
from PIL import Image


def resize_image(image_path: str, max_size=512):

    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size))
        img.save(image_path, quality=85)  # Save with reduced quality if necessary


async def process_images(elements: List[ElementBased]) -> List[str]:
    img_paths = []
    for element in elements:
        if "image" in element.mime:
            resize_image(element.path)
            img_paths.append(element.path)
    return img_paths


async def handle_user_input(
    user_input: str,
    img_paths: List[str],
    session_id: str,
):
    chain = build_vision_chat_chain(get_llm(), DEFAULT, img_paths)
    inp = {"user_input": user_input}
    msg = cl.Message(content="")
    async for chunk in chain.astream(
        inp, config={"configurable": {"session_id": session_id}}
    ):
        if chunk:
            await msg.stream_token(chunk)
    await msg.update()


@cl.on_message
async def chat(message: cl.Message):
    session_id = cl.user_session.get("id")
    images = [file for file in message.elements if "image" in file.mime]
    img_paths = await process_images(images)
    await handle_user_input(message.content, img_paths, session_id)


@cl.on_audio_chunk
async def audio_input(chunk: cl.AudioChunk):
    if chunk.isStart:
        buffer = BytesIO()
        cl.user_session.set("audio_buffer", buffer)
    cl.user_session.get("audio_buffer").write(chunk.data)


@cl.on_audio_end
async def on_audio_end(elements: list[ElementBased]):
    # Get the audio buffer from the session
    audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
    user_input = transcribe_audio(audio_buffer)
    await cl.Message(
        author="You",
        type="user_message",
        content=user_input,
    ).send()
    session_id = cl.user_session.get("id")
    img_paths = await process_images(elements)
    await handle_user_input(user_input, img_paths, session_id)
