

// Initialize the webcam and set event listeners
function initializeWebcam() {
    const video = document.getElementById('webcam');
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(error => {
            console.error('getUserMedia error:', error);
            // You can update this to show an error message to the user in the UI.
        });
}

// Function to capture image from webcam and process it
function captureImage() {
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64Image = canvas.toDataURL('image/jpeg').split(',')[1];
    console.log(base64Image);
    processImage(base64Image);
}

// Send the image to the server for processing
function processImage(base64Image) {
    toggleLoader(true); // Show the loader

    fetch('process_image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image: base64Image })
    })
    .then(response => response.json())
    .then(handleResponse)
    .catch(handleError)
    .then(playvoice);
}

// Handle the server response
function handleResponse(data) {
    toggleLoader(false); // Hide the loader
    if(data.error) {
        console.error(data.error);
        appendToChatbox(`Error: ${data.error}`, true);
        return;
    }
    appendToChatbox(data.choices[0].message.content);
}

// Handle the server response for audio
function handleResponse2(data){
    toggleLoader(false);
    if (data.error){
        console.error(data.error);
        appendToChatbox(`Error: ${data.error}`, true);
        return;
    }
    // Change this for deepgram response
    data = data.results.channels[0].alternatives[0].transcript;

    appendToChatbox(data, true);
    fetch('process_response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
            },
        }
    )
    .then(response => response.json())
    .then(handleResponse)
    .catch(handleError);

}

// Play the voice response
function playvoice(){
    var audioplayer = document.getElementById('audio');
    audioplayer.src = "output.mp3";
    audioplayer.crossOrigin = 'anonymous';
    audioplayer.play();
}

// Handle any errors during fetch
function handleError(error) {
    toggleLoader(false); // Hide the loader
    console.error('Fetch error:', error);
    appendToChatbox(`Error: ${error.message}`, true);
}

// Toggle the visibility of the loader
function toggleLoader(show) {
    document.querySelector('.loader').style.display = show ? 'block' : 'none';
}

// Append messages to the chatbox
function appendToChatbox(message, isUserMessage = false) {
    const chatbox = document.getElementById('chatbox');
    const messageElement = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString(); // Get the current time as a string
    
    // Assign different classes based on the sender for CSS styling
    messageElement.className = isUserMessage ? 'user-message' : 'assistant-message';

    messageElement.innerHTML = `<div class="message-content">${message}</div>
                                <div class="timestamp">${timestamp}</div>`;
    if (chatbox.firstChild) {
        chatbox.insertBefore(messageElement, chatbox.firstChild);
    } else {
        chatbox.appendChild(messageElement);
    }
}

// Function to switch the camera source
function switchCamera() {
    const video = document.getElementById('webcam');
    let usingFrontCamera = true; // This assumes the initial camera is the user-facing one

    return function() {
        // Toggle the camera type
        usingFrontCamera = !usingFrontCamera;
        const constraints = {
            video: { facingMode: (usingFrontCamera ? 'user' : 'environment') }
        };
        
        // Stop any previous stream
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
        
        // Start a new stream with the new constraints
        navigator.mediaDevices.getUserMedia(constraints)
            .then(stream => {
                video.srcObject = stream;
            })
            .catch(error => {
                console.error('Error accessing media devices.', error);
            });
    };
}
// Access microphone

// Record audio
navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);

        // Start recording when the space key is pressed, and stop when it's released
        document.addEventListener('keydown', function(e) {
            if (e.code === 'Space') {
                mediaRecorder.start();
            }
        });

        document.addEventListener('keyup', function(e) {
            if (e.code === 'Space') {
                mediaRecorder.stop();
            }
        });

        mediaRecorder.ondataavailable = function(e) {
            const audioChunks = [];
            let audioBlob = null;
            audioChunks.push(e.data);
            if (mediaRecorder.state === 'inactive') {
                audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
            }

            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = function() {

                // testing out through audio
                // let url = reader.result;
                // let audio = document.getElementById('audio');
                // audio.src = url;
                // audio.crossOrigin = 'anonymous';
                // audio.play();

                let formData = new FormData();
                formData.append('audio', audioBlob, 'input.mp3');
                fetch('process_audio', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(handleResponse2)
                .catch(handleError);
                // .then(handleResponse2);
            };
        };
    });
// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    initializeWebcam();

    document.getElementById('capture').addEventListener('click', captureImage);
    document.getElementById('switch-camera').addEventListener('click', switchCamera());

    // Other event listeners here...
});


export {initializeWebcam, captureImage, switchCamera, processImage, appendToChatbox};