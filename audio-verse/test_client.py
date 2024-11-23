import json

import pyaudio
import websockets

# Initialize PyAudio
p = pyaudio.PyAudio()

# Set up audio playback stream
stream = p.open(
    format=pyaudio.paInt16,  # 16-bit PCM
    channels=1,  # Mono
    rate=24000,  # 24kHz sample rate
    output=True,
    frames_per_buffer=2048,
)


async def websocket_audio_client(uri: str, user_input: str):

    async with websockets.connect(uri) as websocket:
        # Send an initial message to start audio streaming
        await websocket.send(
            json.dumps({"type": "text", "content": user_input, "session_id": "12345"})
        )
        try:
            async for message in websocket:
                if isinstance(message, bytes):  # PCM audio chunk
                    stream.write(message)  # Write PCM data to audio playback stream

                elif isinstance(message, str):  # Text message or end signal
                    data = json.loads(message)
                    message_type = data.get("type")

                    if message_type == "text":
                        content = data.get("content", "")
                        print(content, end="", flush=True)

                    elif message_type == "end":
                        print("\n[Audio stream complete]")
                        break
        finally:
            # Stop and close the audio stream
            stream.stop_stream()
            stream.close()
            p.terminate()


if __name__ == "__main__":
    import asyncio

    text = "tell me a story about Enistein."
    uri = "wss://31b7fh-dtz1gry1tg5e.bdhz.lanrui.co/ws/chat"
    asyncio.run(websocket_audio_client(uri, text))
