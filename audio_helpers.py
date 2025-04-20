import requests
import tempfile
import os
from werkzeug.utils import secure_filename
from config import Config

def text_to_speech(text):
    voice_id = "DMyrgzQFny3JI1Y1paM5"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key":  Config.ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to generate speech: {response.text}")

def save_audio_file(audio_data):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='audio_files') as tmpfile:
        tmpfile.write(audio_data)
        return tmpfile.name