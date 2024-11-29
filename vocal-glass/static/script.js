// DOM Elements
const cameraFeed = document.getElementById('cameraFeed');
const capturePhotoButton = document.getElementById('capturePhoto');
const flipCameraButton = document.getElementById('flipCamera');
const toggleRecordingButton = document.getElementById('toggleRecording');
const submitDataButton = document.getElementById('submitData');
const photoPreview = document.getElementById('photoPreview');
const audioPlayback = document.getElementById('audioPlayback');
const responseText = document.getElementById('responseText');
const responseAudio = document.getElementById('responseAudio');
const responseOutput = document.getElementById('responseOutput');
const captureCanvas = document.createElement('canvas');

let stream = null;
let isFrontCamera = true;
let mediaRecorder = null;
let audioChunks = [];
let audioBlob = null;
let photoBlob = null;

// Disable the submit button initially
submitDataButton.disabled = true;

// Generate a unique session ID for each interaction
const sessionId = `session_${Date.now()}`;

// Start Camera
async function startCamera() {
  const constraints = {
    video: { facingMode: isFrontCamera ? 'user' : 'environment' },
  };
  try {
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    cameraFeed.srcObject = stream;
  } catch (error) {
    alert('Error accessing camera.');
    console.error(error);
  }
}

// Stop Camera
function stopCamera() {
  if (stream) stream.getTracks().forEach((track) => track.stop());
}

// Flip Camera
flipCameraButton.addEventListener('click', () => {
  stopCamera();
  isFrontCamera = !isFrontCamera;
  startCamera();
});

// Capture Photo
capturePhotoButton.addEventListener('click', () => {
  const context = captureCanvas.getContext('2d');
  const { videoWidth, videoHeight } = cameraFeed;

  captureCanvas.width = videoWidth;
  captureCanvas.height = videoHeight;
  context.drawImage(cameraFeed, 0, 0, videoWidth, videoHeight);

  const imageData = captureCanvas.toDataURL('image/png');
  photoPreview.src = imageData;
  photoPreview.classList.remove('hidden');
  photoBlob = dataURLtoBlob(imageData); // Store the photo blob

  // Enable submit button when an image is captured
  submitDataButton.disabled = false;
});

// Audio Recording
async function startAudioRecording() {
  const audioStream = await navigator.mediaDevices.getUserMedia({
    audio: true,
  });
  mediaRecorder = new MediaRecorder(audioStream);

  audioChunks = [];
  mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
  mediaRecorder.onstop = () => {
    audioBlob = new Blob(audioChunks, { type: 'audio/wav' }); // Store the audio blob
    const audioUrl = URL.createObjectURL(audioBlob);
    audioPlayback.src = audioUrl;
    audioPlayback.classList.remove('hidden');
  };

  mediaRecorder.start();
  toggleRecordingButton.textContent = 'Stop Recording';
}

function stopAudioRecording() {
  mediaRecorder.stop();
  toggleRecordingButton.textContent = 'Start Recording';
}

// Toggle Audio Recording
toggleRecordingButton.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopAudioRecording();
  } else {
    startAudioRecording();
  }
});

// Submit Data
submitDataButton.addEventListener('click', () => {
  if (!photoBlob) {
    alert('Please capture a photo before submitting.');
    return;
  }

  const formData = new FormData();
  formData.append('session_id', sessionId); // Include session_id as a form field
  formData.append('photo', photoBlob, 'photo.png');
  if (audioBlob) {
    formData.append('audio', audioBlob, 'audio.wav');
  }

  // Show the spinner and disable the submit button
  const spinner = document.getElementById('spinner');
  spinner.classList.remove('hidden');
  submitDataButton.disabled = true;

  fetch('/submit', {
    method: 'POST',
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      responseOutput.classList.remove('hidden');
      responseText.textContent = data.text;

      if (data.audio_url) {
        responseAudio.src = data.audio_url;
        responseAudio.classList.remove('hidden');
      }
    })
    .catch((error) => {
      console.error('Error submitting data:', error);
    })
    .finally(() => {
      // Hide the spinner and re-enable the submit button
      spinner.classList.add('hidden');
      submitDataButton.disabled = false;
    });
});

// Utility: Convert DataURL to Blob
function dataURLtoBlob(dataURL) {
  const [header, base64] = dataURL.split(',');
  const mime = header.match(/:(.*?);/)[1];
  const binary = atob(base64);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);
  return new Blob([array], { type: mime });
}

// Initialize Camera
startCamera();
