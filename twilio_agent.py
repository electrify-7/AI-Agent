import requests
import os
import tempfile
from flask import Flask, request, jsonify, url_for, session, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import openai
from werkzeug.utils import secure_filename
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # Load environment variables from .env file

gclient = Groq(api_key='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')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app_public_url = os.getenv('APP_PUBLIC_URL')
app_public_gather_url = f"{app_public_url}/gather"
app_public_event_url = f"{app_public_url}/event"

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
from_number = os.getenv('TWILIO_FROM_NUMBER')

openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key  # Set the OpenAI key

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('VOICE_ID')

client = Client(account_sid, auth_token)


def save_audio_file(audio_data):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='audio_files') as tmpfile:
        tmpfile.write(audio_data)
        return tmpfile.name

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('audio_files', filename)

def text_to_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/jsCqWAovK2LkecY7zXl4"
    headers = {
        'Content-Type': 'application/json',
        'xi-api-key': ELEVENLABS_API_KEY
    }
    data = {
        "model_id": "eleven_monolingual_v1",
        "text": text,
        "voice_settings": {
            "similarity_boost": 0.8,
            "stability": 0.5,
            "use_speaker_boost": True
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to generate speech: {response.text}")

def process_initial_message(customer_name, customer_businessdetails):
    # This is a placeholder for your actual function logic.
    # It should return a string based on the input parameters.
    message_history = [
        {
            "role": "system",
            "content": """Remember, your name is 'Sally', You're an expert Sales Representative at Kno2gether, an AI Automation Agency specializing in business process automation through AI. 
            Following a customer's inquiry via our website, you're initiating a cold call to progress them further in the sales journey. 
            As you are initiating the call, Very Briefly introduce yourself.
            Keep the potential customer engaged by not respoding too lengthy response. You are expert in Sales, you know it better.
            Make sure to keep it short and professional.
            """
        }
    ]

    initial_transcript = "Customer Name:" + customer_name + ". Customer's business Details as filled up in the website:" + customer_businessdetails
    message_history.append({"role": "user", "content": initial_transcript})
    session['message_history'].append({"role": "user", "content": initial_transcript})
    chat_completion = gclient.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=message_history,
                temperature=0.5,
                max_tokens=100,
                stream=False,
                top_p=1
            )
    assistant_response = chat_completion.choices[0].message.content
    session['message_history'].append({"role": "assistant", "content": assistant_response})
    session.modified = True
    return assistant_response

def process_message(speech_result):
    if 'message_history' not in session:
        # Initialize it if not present (optional, based on your flow)
        session['message_history'] = []
    # This is a placeholder for your actual function logic.
    # It should return a string based on the input parameters.
    message_history = session['message_history']
    print("-------------------Before Processing---------------------------")
    for message in message_history:
        if 'content' in message:
            print(message['content'])
    message_history.append({"role": "system", "content":  """You're an expert Sales Representative at Kno2gether (spelled 'Know Together'), an AI Automation Agency. As you are continuing the phone conversation
                            Your goal during this conversation is to guide the potential customer through the sales process, aiming to secure a meeting via Calendly. 
                            Based on the customer's last interaction and the message history, respond appropriately within the conversation stage you're in, using a short, professional tone. 
                            The stages are: 1) Asking Open Ended questions on customer's problem, 2) Solution Presentation, 3) Objection Handling, 4) Close, and 5) End Conversation. If at 'End Conversation,' simply thank them. 
                            Always consider the conversation stage before responding and keep the conversation short, engaging and specific to a stage. 
                            DO NOT MENTION WHAT STAGE YOU ARE TO THE CUSTOMER IN YOUR RESPONSE AND DO NOT CREATE NUMBERED RESPONSE as this is a telephonic conversation.
                            Just for your knowledge, Kno2gether offers an AI Development Subscription starting at $3999/month for unlimited AI design/development tasks, managed through a Trello Dashboard, with a 4-day average completion time per task.
            """})

    message_history.append({"role": "user", "content": speech_result})
    chat_completion = gclient.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=message_history,
                temperature=0.5,
                max_tokens=100,
                stream=False,
                top_p=1
            )  
    assistant_response = chat_completion.choices[0].message.content
    message_history.append({"role": "assistant", "content": assistant_response})
    session['message_history'] = message_history
    session.modified = True

    print("-------------------After Processing---------------------------")
    for message in message_history:
    # Check if the message dictionary has a 'content' key
        if 'content' in message:
        # Print the content of the message
            print(message['content'])

    return assistant_response

@app.route('/start-call', methods=['POST'])
def start_call():
    
    """Initiates the call to the customer."""
    # Extract the JSON data sent with the POST request
    session['message_history'] = []
    data = request.json
    customer_name = data.get('customer_name', '')
    customer_phonenumber = data.get('customer_phonenumber', '')
    customer_businessdetails = data.get('customer_businessdetails', '')

    # Use the extracted data to process the initial message
    initial_message = process_initial_message(customer_name, customer_businessdetails)
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    response = VoiceResponse()
    # response.say(initial_message, voice="Polly.Joanna")
    response.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    print("Start Call - Session:", dict(session))
    # Directly use the ngrok URL for redirection
    response.redirect(app_public_gather_url)

    # to_number = customer_phonenumber  # Ensure this is the correct variable for the recipient's number
    # from_number = 'your_twilio_number'  # Your Twilio number

    call = client.calls.create(
        twiml=str(response),
        to=customer_phonenumber,
        from_=from_number,
        method="GET",
        status_callback=app_public_event_url,
        status_callback_method="POST"
    )
    return jsonify({'message': 'Call initiated', 'call_sid': call.sid})

@app.route('/gather', methods=['GET', 'POST'])
def gather_input():
    """Gathers customer's speech input for both inbound and outbound calls."""
    resp = VoiceResponse()
    print("Gather - Session before setup:", dict(session)) 
    gather = Gather(input='speech', action='/process-speech', speechTimeout='auto', method="POST")
    resp.append(gather)
    resp.redirect('/gather')
    print("Gather - Session after setup:", dict(session)) 
    return str(resp)


@app.route('/gather-inbound', methods=['GET', 'POST'])
def gather_input_inbound():
    """Gathers customer's speech input for both inbound and outbound calls."""
    resp = VoiceResponse()
    print("Gather - Session before setup:", dict(session))  
    if 'message_history' not in session:
        print("Initializing for inbound call...")
        session['message_history'] = []
        agent_response = "Hi, This is Sally from Kno2gether. Thank you for calling us. Please let me know how can I help you today?"
        audio_data = text_to_speech(agent_response)
        audio_file_path = save_audio_file(audio_data)
        audio_filename = os.path.basename(audio_file_path)
        resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
        session['message_history'].append({"role": "assistant", "content": agent_response})
        session.modified = True
        resp.redirect('/gather')
    print("Gather - Session after setup:", dict(session)) 
    return str(resp)

@app.route('/process-speech', methods=['POST'])
def process_speech():
    """Processes customer's speech input and responds accordingly."""
    speech_result = request.values.get('SpeechResult', '')
    
    # Generate AI response (simplified, adjust based on your logic and OpenAI's capabilities)
    response= process_message(speech_result)
    audio_data = text_to_speech(response)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)
    
    resp = VoiceResponse()
    # resp.say(response, voice='Polly.Joanna')
    resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    resp.redirect('/gather')  # Continue the conversation
    return str(resp)

@app.route('/event', methods=['POST'])
def event():
    call_status = request.values.get('CallStatus', '')
    if call_status in ['completed', 'busy', 'failed']:
        # Log or process the session['message_history'] as needed
        session.pop('message_history', None)  # Clean up after the call
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
