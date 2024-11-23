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

                elif isinstance(message, str):  # Text message
                    data = json.loads(message)
                    content = data.get("content", "")
                    print(content, end="", flush=True)

        finally:
            # Stop and close the audio stream
            stream.stop_stream()
            stream.close()
            p.terminate()
