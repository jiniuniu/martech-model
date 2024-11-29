import asyncio
import os

import aiohttp
import shortuuid
from config import env_settings
from loguru import logger
from storage_conn.qiniu_conn import get_qiniu


async def call_tts(text: str) -> str | None:
    tts_url = f"{env_settings.voice_server_url}/tts"
    async with aiohttp.ClientSession() as session:
        async with session.post(tts_url, json={"text": text}) as response:
            if response.status == 200:
                filename = shortuuid.ShortUUID().random(11)
                file_path = f"/tmp/{filename}.ogg"

                # Write the audio content (ogg) to a file
                with open(file_path, "wb") as audio_file:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        audio_file.write(chunk)
                if os.path.exists(file_path):
                    q = get_qiniu()
                    file_key = q.upload_file(file_path, "audio_assets")
                    audio_url = q.get_public_url(file_key)
                    logger.info(f"audio url: {audio_url}")
                    return audio_url
            else:
                logger.error(
                    f"Error calling /tts: {response.status}, {await response.text()}"
                )


async def call_stt(audio_bytes: bytes) -> str | None:
    stt_url = f"{env_settings.voice_server_url}/stt"

    # Create a FormData object to send the file
    data = aiohttp.FormData()
    data.add_field(
        "file",
        audio_bytes,
        filename="audio.ogg",
        content_type="audio/ogg",
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(stt_url, data=data) as response:
            if response.status == 200:
                result = await response.json()
                transcription = result.get("transcription")
                logger.info(f"Transcription: {transcription}")
                return transcription
            else:
                logger.error(
                    f"Error calling /stt: {response.status}, {await response.text()}"
                )


# Run the main function
if __name__ == "__main__":
    res = asyncio.run(
        call_tts(
            "Hello, this is a test. I am testing my tts client code and uploading to the blob storage."
        )
    )
    print(res)
