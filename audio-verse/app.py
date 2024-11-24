from chains import build_chat_chain
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger
from prompts import CHAT_SYS_MSG
from tts import text_to_speech

chat_chain = build_chat_chain(CHAT_SYS_MSG)


app = FastAPI()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted.")

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            content = data.get("content")
            session_id = data.get("session_id", "abc")

            if message_type == "text":
                logger.info(f"Received text: {content}")
                await generate_response(websocket, session_id, content)

            elif message_type == "disconnect":
                logger.info("Received disconnect request.")
                break

    except WebSocketDisconnect:
        logger.warning("WebSocket connection closed.")
    except Exception as e:
        logger.error(f"Error in WebSocket communication: {e}")
    finally:
        logger.info("WebSocket endpoint terminated.")


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
            await websocket.send_json({"type": "text", "content": chunk})
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
    # Send an "end" message to signal that the audio stream is complete
    await websocket.send_json({"type": "end", "content": "Audio stream complete"})


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=27777)
