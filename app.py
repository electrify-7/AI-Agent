from flask import Flask, request, jsonify, url_for, after_this_request, send_from_directory, abort
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from werkzeug.utils import secure_filename
from langchain_core.prompts import PromptTemplate
import os
import json
import uuid
import logging
import threading
import time

from audio_helpers import text_to_speech, save_audio_file
# from conversation import post_conversation_update
from ai_helpers import process_initial_message, process_message, initiate_inbound_message
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Directory for temporary audio files (already in use)
AUDIO_DIR = 'audio_files'
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# Directory-based storage for conversation histories (replaces Redis)
DATA_DIR = 'conversations'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def save_conversation(unique_id, message_history):
    path = os.path.join(DATA_DIR, f"{unique_id}.json")
    with open(path, 'w') as f:
        json.dump(message_history, f)


def load_conversation(unique_id):
    path = os.path.join(DATA_DIR, f"{unique_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def delete_conversation(unique_id):
    path = os.path.join(DATA_DIR, f"{unique_id}.json")
    try:
        os.remove(path)
        logger.info(f"Deleted conversation history for {unique_id}")
    except OSError as e:
        logger.error(f"Error deleting conversation file {path}: {e}")

# Twilio client
client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config.from_object(Config)
app.logger.setLevel(logging.DEBUG)


def clean_response(unfiltered_response_text):
    return unfiltered_response_text.replace("<END_OF_TURN>", "").replace("<END_OF_CALL>", "")


def delayed_delete(filename, delay=5):
    def attempt_delete():
        time.sleep(delay)
        try:
            os.remove(filename)
            logger.info(f"Deleted temporary audio file: {filename}")
        except Exception as error:
            logger.error(f"Error deleting audio file {filename}: {error}")

    thread = threading.Thread(target=attempt_delete)
    thread.start()


@app.route('/audio/<filename>')
def serve_audio(filename):
    directory = AUDIO_DIR

    @after_this_request
    def remove_file(response):
        full_path = os.path.join(directory, filename)
        delayed_delete(full_path)
        return response

    try:
        return send_from_directory(directory, filename)
    except FileNotFoundError:
        logger.error(f"Audio file not found: {filename}")
        abort(404)


@app.route('/start-call', methods=['POST'])
def start_call():
    unique_id = str(uuid.uuid4())
    data = request.json or {}
    customer_name = data.get('customer_name', 'Valued Customer')
    customer_phonenumber = data.get('customer_phonenumber', '')
    customer_businessdetails = data.get('customer_businessdetails', 'No details provided.')

    # AI initial message
    ai_message = process_initial_message(customer_name, customer_businessdetails)
    initial_message = clean_response(ai_message)

    # Text-to-speech
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    # Initialize message history and persist to file
    initial_transcript = (
        f"Customer Name: {customer_name}. "
        f"Customer's business details: {customer_businessdetails}"
    )
    history = [
        {"role": "user", "content": initial_transcript},
        {"role": "assistant", "content": initial_message}
    ]
    save_conversation(unique_id, history)
    # post_conversation_update(unique_id, history)
    try:
        import requests
        requests.post(
            "http://localhost:5000/conversation",
            json={"messages": history},
            timeout=2
        )
    except Exception as e:
        logger.warning(f"Failed to send to /conversation: {e}")



    # Build TwiML response
    response = VoiceResponse()
    response.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    redirect_url = f"{Config.APP_PUBLIC_GATHER_URL}?CallSid={unique_id}"
    response.redirect(redirect_url)

    # Initiate outbound call
    call = client.calls.create(
        twiml=str(response),
        to=customer_phonenumber,
        from_=Config.TWILIO_FROM_NUMBER,
        method="GET",
        status_callback=Config.APP_PUBLIC_EVENT_URL,
        status_callback_method="POST"
    )
    return jsonify({'message': 'Call initiated', 'call_sid': call.sid})


@app.route('/gather', methods=['GET', 'POST'])
def gather_input():
    call_sid = request.args.get('CallSid', '')
    resp = VoiceResponse()
    gather = Gather(
        input='speech',
        action=url_for('process_speech', CallSid=call_sid),
        speechTimeout='auto',
        method="POST"
    )
    resp.append(gather)
    resp.redirect(url_for('gather_input', CallSid=call_sid))
    return str(resp)


@app.route('/gather-inbound', methods=['GET', 'POST'])
def gather_input_inbound():
    resp = VoiceResponse()
    unique_id = str(uuid.uuid4())

    agent_response = initiate_inbound_message()
    audio_data = text_to_speech(agent_response)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))

    # Save initial inbound history
    history = [{"role": "assistant", "content": agent_response}]
    save_conversation(unique_id, history)
    # post_conversation_update(unique_id, history)
    try:
        import requests
        requests.post(
            "http://localhost:5000/conversation",
            json={"messages": history},
            timeout=2
        )
    except Exception as e:
        logger.warning(f"Failed to send to /conversation: {e}")



    resp.redirect(url_for('gather_input', CallSid=unique_id))
    return str(resp)


@app.route('/process-speech', methods=['POST'])
def process_speech():
    speech_result = request.values.get('SpeechResult', '').strip()
    call_sid = request.args.get('CallSid', '')

    history = load_conversation(call_sid)

    ai_response_text = process_message(history, speech_result)
    response_text = clean_response(ai_response_text)

    audio_data = text_to_speech(response_text)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    resp = VoiceResponse()
    resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    if "<END_OF_CALL>" in ai_response_text:
        resp.hangup()
    else:
        resp.redirect(url_for('gather_input', CallSid=call_sid))

    # Update and persist history
    history.append({"role": "user", "content": speech_result})
    history.append({"role": "assistant", "content": response_text})
    save_conversation(call_sid, history)
    # history[-2:] is exactly the [user, assistant] we just added
    # post_conversation_update(call_sid, history[-2:])


    # Also send new messages to live stream UI
    try:
        import requests
        requests.post(
            "http://localhost:5000/conversation",
            json={"messages": history[-2:]},
            timeout=2
        )
    except Exception as e:
        logger.warning(f"Failed to send to /conversation: {e}")


    return str(resp)


@app.route('/event', methods=['POST'])
def event():
    call_status = request.values.get('CallStatus', '')
    call_sid = request.values.get('CallSid', '')
    if call_status in ['completed', 'busy', 'failed'] and call_sid:
        delete_conversation(call_sid)
        logger.info(f"Call {call_sid} ended with status: {call_status}")
    return ('', 204)



global CONVERSATION_HISTORY, STREAM_QUEUES
from flask import Response
import queue


CONVERSATION_HISTORY = []
STREAM_QUEUES = []

@app.route('/conversation', methods=['POST'])
def receive_conversation():
    global CONVERSATION_HISTORY, STREAM_QUEUES  # ← ADD THIS

    messages = request.json.get("messages", [])
    if not isinstance(messages, list):
        return jsonify({"error": "Invalid format"}), 400

    # Append to history
    CONVERSATION_HISTORY.extend(messages)

    # Notify all connected stream listeners
    for q in STREAM_QUEUES:
        for msg in messages:
            q.put(msg)

    return '', 204


@app.route('/conversation', methods=['GET'])
def get_conversation():
    return jsonify(CONVERSATION_HISTORY)


@app.route('/stream')
def stream():
    global CONVERSATION_HISTORY, STREAM_QUEUES
    q = queue.Queue()
    STREAM_QUEUES.append(q)

    def event_stream():
        try:
            while True:
                msg = q.get()
                yield f"data: {json.dumps(msg)}\n\n"
        except GeneratorExit:
            STREAM_QUEUES.remove(q)

    return Response(event_stream(), content_type='text/event-stream')






if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
