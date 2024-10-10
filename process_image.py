import os
import json
from deepgram import (DeepgramClient, FileSource)
from deepgram import PrerecordedOptions
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import base64
import time
import os
from deepgram import SpeakOptions
import requests
from flask import Flask, request, jsonify

app = Flask(__name__, static_folder='src', static_url_path='/')
socketio = SocketIO(app)
# Replace 'YOUR_DEFAULT_API_KEY' with the name of the environment variable
OPEN_API_KEY = os.environ.get('OPEN_API_KEY', 'OPEN_API_KEY')
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY', 'DEEPGRAM_API_KEY')
STORAGE = "C:\\Users\\manht\\OneDrive\\Documents\\Project\\AICore\\WebcamGPT-Vision\\python-version\\src\\chat_history\\chat_history.json"

# FileChangeHandler class to handle file creation events
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, socketio):
        self.socketio = socketio
    def on_created(self, event):
        if not event.is_directory and ((event.src_path.endswith('.jpeg') or event.src_path.endswith('.png'))):
            print(f'Image created: {event.src_path}')
            temp = os.path.join(os.getcwd(),"src",  "image_files", event.src_path.split("\\")[-1])

            for _ in range(3):
                try: 
                    f = open(temp, 'rb')

                    base64_image = f.read()
                    base64_encoded_image = base64.b64encode(base64_image).decode('utf-8')
                    self.socketio.emit('image_created', {'base64_image': base64_encoded_image})
                    return
                except FileNotFoundError:
                    print("File not found")
                    time.sleep(1)

# Starting the file watcher, tracking the image_files directory
def start_watcher(path):
    event_handler = FileChangeHandler(socketio)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Store chat history to a JSON file
def store_chat_history(data):
    with open(STORAGE, 'r') as f:
        chat_history = json.load(f)
    
    chat_history["content"].append(data)
    
    with open(STORAGE, 'w') as f:
        json.dump(chat_history, f)

# Get chat history from a JSON file AS A STRING
def get_chat_history():
    print(STORAGE)
    with open(STORAGE, 'r') as f:
        chat_history = json.load(f)
        chat_history = str(chat_history["content"])
    return chat_history
# Index route
@app.route('/')
def index():
    """Return the index.html page."""
    return app.send_static_file('index.html')

# Process image file
@app.route('/process_image', methods=['POST'])
def process_image():
    data = request.json
    base64_image = data.get('image', '')

    if base64_image:
        api_key = OPEN_API_KEY
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        chat_history = get_chat_history()

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"What’s in this image? Be descriptive. For each significant item recognized, wrap this word in <b> tags. Example: The image shows a <b>man</b> in front of a neutral-colored <b>wall</b>. He has short hair, wears <b>glasses</b>, and is donning a pair of over-ear <b>headphones</b>. ... Also output an itemized list of objects recognized, wrapped in <br> and <b> tags with label <br><b>Objects:.\
                                Please also listen to chat history for changes in request: {chat_history}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        # Deepgram config for text-to-speech
        TEXT = {
            "text": json.loads(response.content)['choices'][0]['message']['content']
        }

        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        options = SpeakOptions(
            model = 'aura-asteria-en',
        )

        temp = deepgram.speak.v("1").save("./src/output.mp3", TEXT, options)
        print(temp.to_json(indent=4))
        if response.status_code != 200:
            return jsonify({'error': 'Failed to process the image.'}), 500
        
        # Save chat history as assistant role
        store_chat_history({
            "role": "assistant",
            "content": response.content.decode('utf-8')
        })
        
        return response.content

    else:
        return jsonify({'error': 'No image data received.'}), 400


PROMPT = "We kind of need an actual prompt here"
# Process audio file
@app.route('/process_audio', methods=['POST'])
def process_audio():
    print(request.files)
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file received.'}), 400
    
    audio = request.files['audio']

    save_path = os.path.join(os.getcwd(), "src", "audio_files", audio.filename)
    print(save_path)
    with open(save_path, 'wb') as f:
        f.write(audio.read())
    try:
        # Deepgram config for speech-to-text
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)


        options = PrerecordedOptions(
            model = 'nova',
            language = 'en',
            smart_format=True,
        )

        # Load the audio file
        with open(save_path, 'rb') as f:
            buffer_data = f.read()

            payload: FileSource = {
                "buffer" : buffer_data,
            }
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

        print(response)

        #extract text from response
        text_response = response["results"]["channels"][0]["alternatives"][0]["transcript"]

        # Save chat history as user role
        store_chat_history({
            "role": "user",
            "content": text_response
        })


        return response.to_json()
    except Exception as e:
        print(f"Error: {e}")

        return jsonify({'error': 'Failed to process the audio.'}), 500

# Process current chat history and make a response
@app.route('/process_response', methods=['POST'])
def process_response():
    try:
        api_key = OPEN_API_KEY
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        chat_history = get_chat_history()

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text":  "Listen to the chat history, extract the last response and follow the instruction \
                                if it's a request. If it's a question, answer it. If it's a request, follow the instruction. If it's a statement, respond accordingly. Also output an itemized list of objects recognized, wrapped in <br> and <b> tags with label <br><b>Objects:.\
                                Chat History: " + chat_history + "Only return your response. Do not include the chat history in your response."
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            return jsonify({'error': 'Failed to process the response.'}), 500
        
        print("Debug0")
        print(response.content.decode('utf-8'))
        print("Debug1")
          # Save chat history as assistant role
        store_chat_history({
            "role": "assistant",
            "content": response.content.decode('utf-8')
        })
        
        print("Debugging")
        return response.content
    except Exception as e:
        print(f"Error: {e}")

        return jsonify({'error': 'Failed to process the response.'}), 500

def delete_chat_history():
    with open(STORAGE, 'w') as f:
        json.dump({"content": []}, f)
if __name__ == '__main__':
   
    delete_chat_history()
    path = os.getcwd()+ '\src\image_files'
    # watcher_thread = threading.Thread(target=start_watcher, args=(path,))
    # watcher_thread.start()
    app.run(debug=True)
