document.addEventListener('DOMContentLoaded', () => {
    const transcriptionText = document.getElementById('transcriptionText');
    const responseText = document.getElementById('responseText');
    const startRecordBtn = document.getElementById('startRecordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');

    let socket;
    let mediaRecorder;
    let audioContext;
    let audioSource;
    let audioChunks = [];
    let isReceivingAudio = false;

    function initWebSocket() {
        // Use relative WebSocket URL to work with different deployments
        socket = new WebSocket(`ws://${window.location.host}/ws/chat`);
        audioContext = new (window.AudioContext || window.webkitAudioContext)();

        socket.onopen = () => {
            console.log('WebSocket connection established');
            startRecordBtn.disabled = false;
        };

        socket.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // Accumulate audio chunks
                if (!isReceivingAudio) {
                    audioChunks = [];
                    isReceivingAudio = true;
                }
                audioChunks.push(event.data);
            } else {
                // Handle text messages
                const data = JSON.parse(event.data);
                
                if (data.type === 'transcription') {
                    transcriptionText.textContent = data.content;
                    transcriptionText.classList.add('italic');
                }
                
                if (data.type === 'response_text') {
                    responseText.textContent += data.content;
                }

                if (data.type === 'audio_end') {
                    // Combine all audio chunks and play
                    if (isReceivingAudio) {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        playTTSAudio(audioBlob);
                        audioChunks = [];
                        isReceivingAudio = false;
                    }
                }
            }
        };

        socket.onclose = (event) => {
            console.log('WebSocket connection closed', event);
            startRecordBtn.disabled = true;
            stopRecordBtn.disabled = true;
        };
    }

    function playTTSAudio(audioBlob) {
        const reader = new FileReader();
        reader.onloadend = () => {
            audioContext.decodeAudioData(reader.result, (buffer) => {
                // Create a source buffer
                audioSource = audioContext.createBufferSource();
                audioSource.buffer = buffer;
                
                // Connect to the audio context's destination (speakers)
                audioSource.connect(audioContext.destination);
                
                // Play the audio
                audioSource.start(0);
            }, (e) => {
                console.error('Error decoding audio data', e);
                // Fallback to regular audio playback
                const audio = new Audio(URL.createObjectURL(audioBlob));
                audio.play();
            });
        };
        reader.readAsArrayBuffer(audioBlob);
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new RecordRTC(stream, {
                type: 'audio',
                mimeType: 'audio/webm',
                audioBitsPerSecond: 16000
            });

            mediaRecorder.startRecording();
            
            startRecordBtn.disabled = true;
            stopRecordBtn.disabled = false;
            transcriptionText.textContent = '';
            responseText.textContent = '';
        } catch (error) {
            console.error('Error accessing microphone:', error);
        }
    }

    function stopRecording() {
        mediaRecorder.stopRecording(() => {
            const audioBlob = mediaRecorder.getBlob();
            
            // Send audio blob via WebSocket
            const reader = new FileReader();
            reader.onloadend = () => {
                const audioData = reader.result;
                socket.send(audioData);
                socket.send('stop_recording');
            };
            reader.readAsArrayBuffer(audioBlob);

            startRecordBtn.disabled = false;
            stopRecordBtn.disabled = true;
        });
    }

    // Send periodic ping to keep WebSocket connection alive
    function startPingInterval() {
        setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('pong');
            }
        }, 30000);
    }

    initWebSocket();
    startPingInterval();

    startRecordBtn.addEventListener('click', startRecording);
    stopRecordBtn.addEventListener('click', stopRecording);
});