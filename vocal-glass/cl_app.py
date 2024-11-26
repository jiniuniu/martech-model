import chainlit as cl
from assistants.chains import build_vision_chat_chain
from assistants.llms import get_llm
from assistants.sys_prompts import DEFAULT
from PIL import Image


def resize_image(image_path, max_size=1024):
    with Image.open(image_path) as img:
        img.thumbnail(
            (max_size, max_size)
        )  # Resizes the image while maintaining aspect ratio
        resized_path = (
            f"{image_path.rsplit('.', 1)[0]}_resized.{image_path.rsplit('.', 1)[-1]}"
        )
        img.save(resized_path, quality=85)  # Save with reduced quality if necessary
        return resized_path


@cl.on_message
async def chat(message: cl.Message):
    images = [file for file in message.elements if "image" in file.mime]
    session_id = cl.user_session.get("id")
    msg = cl.Message(content="")

    img_paths = []
    if images:
        img_paths = [resize_image(image.path, max_size=1024) for image in images]
    chain = build_vision_chat_chain(get_llm(), DEFAULT, img_paths)
    inp = {"user_input": message.content}
    async for chunk in chain.astream(
        inp, config={"configurable": {"session_id": session_id}}
    ):
        if chunk:
            await msg.stream_token(chunk)

    await msg.update()
