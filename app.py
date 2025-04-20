from flask import Flask, request, jsonify, url_for, after_this_request, send_from_directory, abort
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from werkzeug.utils import secure_filename
from langchain_core.prompts import PromptTemplate
from groq import Groq

import os
import json
import uuid
import logging
import threading
import time
import requests
import sys

# Configure logging with detailed format and output to stdout for better debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Force unbuffered output for debugging
os.environ['PYTHONUNBUFFERED'] = '1'

from audio_helpers import text_to_speech, save_audio_file
# from conversation import post_conversation_update
from ai_helpers import process_initial_message, process_message, initiate_inbound_message
from config import Config

# Directory for temporary audio files
AUDIO_DIR = 'audio_files'
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)
    print(f"DEBUG: Created audio directory: {AUDIO_DIR}", flush=True)

# Directory-based storage for conversation histories
DATA_DIR = 'conversations'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"DEBUG: Created conversations directory: {DATA_DIR}", flush=True)

# Directory for storing summaries
SUMMARY_DIR = 'summaries'
if not os.path.exists(SUMMARY_DIR):
    os.makedirs(SUMMARY_DIR)
    print(f"DEBUG: Created summaries directory: {SUMMARY_DIR}", flush=True)

# In-memory stores
CONVERSATIONS = {}  # { unique_id: [messages] }
SUMMARIES = {}      # { call_sid: summary_dict }

def save_conversation(unique_id, message_history):
    """Save conversation history to a JSON file"""
    print(f"DEBUG: Saving conversation for call {unique_id} with {len(message_history)} messages", flush=True)
    path = os.path.join(DATA_DIR, f"{unique_id}.json")
    try:
        with open(path, 'w') as f:
            json.dump(message_history, f)
        print(f"DEBUG: Successfully saved conversation to {path}", flush=True)
    except Exception as e:
        print(f"DEBUG ERROR: Failed to save conversation: {str(e)}", flush=True)


def load_conversation(unique_id):
    """Load conversation history from a JSON file"""
    print(f"DEBUG: Loading conversation for call {unique_id}", flush=True)
    path = os.path.join(DATA_DIR, f"{unique_id}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            print(f"DEBUG: Successfully loaded conversation with {len(data)} messages", flush=True)
            return data
        except Exception as e:
            print(f"DEBUG ERROR: Failed to load conversation: {str(e)}", flush=True)
            return []
    print(f"DEBUG: No conversation file found at {path}", flush=True)
    return []


def save_summary(unique_id, summary_data):
    """Save summary to a JSON file"""
    print(f"DEBUG: Saving summary for call {unique_id}", flush=True)
    path = os.path.join(SUMMARY_DIR, f"{unique_id}.json")
    try:
        with open(path, 'w') as f:
            json.dump(summary_data, f)
        print(f"DEBUG: Successfully saved summary to {path}", flush=True)
    except Exception as e:
        print(f"DEBUG ERROR: Failed to save summary: {str(e)}", flush=True)
    logger.info(f"Summary saved to file for call {unique_id}")


def load_summary(unique_id):
    """Load summary from a JSON file"""
    print(f"DEBUG: Loading summary for call {unique_id}", flush=True)
    path = os.path.join(SUMMARY_DIR, f"{unique_id}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            print(f"DEBUG: Successfully loaded summary from {path}", flush=True)
            return data
        except Exception as e:
            print(f"DEBUG ERROR: Failed to load summary: {str(e)}", flush=True)
            return None
    print(f"DEBUG: No summary file found at {path}", flush=True)
    return None


def summariser(message_history, call_sid):
    """
    Generate a summary of the conversation using Groq API.
    
    Args:
        message_history: The conversation history to summarize
        call_sid: The unique call ID
        
    Returns:
        dict: The generated summary in JSON format
    """
    print(f"DEBUG: Starting summarization for call {call_sid}", flush=True)
    print(f"DEBUG: Message history length: {len(message_history)}", flush=True)
    
    try:
        print("DEBUG: Initializing Groq client", flush=True)
        gclient = Groq(api_key="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")
        
        # Format the conversation history as a string
        print("DEBUG: Formatting conversation history", flush=True)
        conversation_text = ""
        for i, msg in enumerate(message_history):
            role = msg.get("role", "")
            content = msg.get("content", "")
            conversation_text += f"{role.capitalize()}: {content}\n\n"
            if i < 2:  # Print first two messages for debugging
                print(f"DEBUG: Message {i}: Role={role}, Content preview={content[:50]}...", flush=True)
        
        print("DEBUG: Preparing messages for LLM", flush=True)
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant that summarizes sales call conversations. Generate a structured JSON summary using specific fields."
            },
            {
                "role": "user",
                "content": f"Given the entire conversation history between a sales agent and a customer, generate a structured JSON summary using the following fields: userid: user id given in history. callid: call id given in history. datetime: the time given in conversation_history. discount: 15.0 — the percentage discount given. name: \"Alice Johnson\" — the full name of the customer. product_name: \"SuperCRM Pro\" — the product discussed or sold. sentiment_score: 0.75 — a value from 0 to 1 indicating customer sentiment. shortDescription: \"Converted to Pro plan with 15% discount.\" — a short summary of the call outcome. sold: 1 — use 1 if the product was sold, else 0. soldPrice: 849.99 — the final price paid by the customer. contactno: Given in message history\n\nConversation History:\n{conversation_text}\n\nRespond in JSON format only. Use the conversation history to generate the JSON response. Do not include any other thing, just JSON. Use _ wherever required."
            }
        ]
        
        print("DEBUG: Calling Groq API", flush=True)
        llm_resp = gclient.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.5,
            max_tokens=4000,
            stream=False,
            top_p=1
        )
        
        print("DEBUG: Received response from Groq API", flush=True)
        raw = llm_resp.choices[0].message.content.strip()
        print(f"DEBUG: Raw response preview: {raw[:100]}...", flush=True)
        
        # Clean up code fences if present
        if raw.startswith('```'):
            raw = raw[7:]
        elif raw.startswith('```'):
            raw = raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
            
        raw = raw.strip()
        print("DEBUG: Parsing JSON response", flush=True)
        summary_json = json.loads(raw)
        
        print(f"DEBUG: JSON parsed successfully with keys: {list(summary_json.keys())}", flush=True)
        
        # Save the summary to file
        print(f"DEBUG: Saving summary to file for call {call_sid}", flush=True)
        save_summary(call_sid, summary_json)
        
        # Also store in memory
        print(f"DEBUG: Storing summary in memory for call {call_sid}", flush=True)
        SUMMARIES[call_sid] = summary_json
        
        print(f"DEBUG: Summary generation complete for call {call_sid}", flush=True)
        logger.info(f"Summary generated for call {call_sid}")
        return summary_json
        
    except json.JSONDecodeError as e:
        print(f"DEBUG ERROR: JSON parsing error: {str(e)}", flush=True)
        print(f"DEBUG ERROR: Raw text that failed to parse: {raw}", flush=True)
        return {"error": "JSON parsing error", "details": str(e)}
    except Exception as e:
        print(f"DEBUG ERROR: Error in summariser: {str(e)}", flush=True)
        print(f"DEBUG ERROR: Exception type: {type(e)}", flush=True)
        import traceback
        print(f"DEBUG ERROR: Traceback: {traceback.format_exc()}", flush=True)
        logger.error(f"Error processing summary: {str(e)}")
        return {"error": "Processing error", "details": str(e)}


def clean_response(unfiltered_response_text):
    """Remove special tokens from AI responses"""
    return unfiltered_response_text.replace("<END_OF_TURN>", "").replace("<END_OF_CALL>", "")


def delayed_delete(filename, delay=5):
    """Delete a file after a delay"""
    def attempt_delete():
        time.sleep(delay)
        try:
            os.remove(filename)
            logger.info(f"Deleted temporary audio file: {filename}")
        except Exception as error:
            logger.error(f"Error deleting audio file {filename}: {error}")

    thread = threading.Thread(target=attempt_delete)
    thread.start()


# Initialize Flask app and Twilio client
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config.from_object(Config)
app.logger.setLevel(logging.DEBUG)

client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve an audio file and schedule it for deletion"""
    print(f"DEBUG: Serving audio file: {filename}", flush=True)
    directory = AUDIO_DIR

    @after_this_request
    def remove_file(response):
        full_path = os.path.join(directory, filename)
        delayed_delete(full_path)
        return response

    try:
        return send_from_directory(directory, filename)
    except FileNotFoundError:
        print(f"DEBUG ERROR: Audio file not found: {filename}", flush=True)
        logger.error(f"Audio file not found: {filename}")
        abort(404)


@app.route('/start-call', methods=['POST'])
def start_call():
    """Initiate an outbound call"""
    print("DEBUG: Received start-call request", flush=True)
    data = request.json or {}
    laptop_data = data.get('laptop_data','')
    print(f"DEBUG: Laptop data: {laptop_data}", flush=True)
    
    unique_id = data.get('callid', str(uuid.uuid4()))
    customer_name = data.get('name', 'Valued Customer')
    customer_phonenumber = data.get('contactno', '')
    customer_businessdetails = data.get('last_call_summary', 'No details provided.')
    customer_datetime = data.get('datetime', '')
    customer_product_name = data.get('product_name', '')
    customer_user_id = data.get('userid', '')
    
    print(f"DEBUG: Starting call for {customer_name} with ID {unique_id}", flush=True)

    # AI initial message
    print("DEBUG: Generating initial AI message", flush=True)
    ai_message = process_initial_message(customer_name, customer_businessdetails)
    initial_message = clean_response(ai_message)

    # Text-to-speech
    print("DEBUG: Converting text to speech", flush=True)
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)
    print(f"DEBUG: Saved audio to {audio_file_path}", flush=True)

    # Initialize message history and persist to file
    initial_transcript = (
        f"Customer Name: {customer_name}. "
        f"Customer Contact Number: {customer_phonenumber}. "
        f"unique  id of call: {unique_id}. "
        f"Customer id: {customer_user_id}. "
        f"Date and Time: {customer_datetime}. "
        f"Customer Product name: {customer_product_name}. "
        f"Customer's business details: {customer_businessdetails}"
        f"Laptop Data: {laptop_data}"
    )
    history = [
        {"role": "user", "content": initial_transcript},
        {"role": "assistant", "content": initial_message}
    ]
    save_conversation(unique_id, history)
    
    # Post to conversation endpoint
    try:
        print(f"DEBUG: Posting initial conversation to /conversation endpoint", flush=True)
        requests.post(
            "http://localhost:5000/conversation",
            json={
                "unique_id": unique_id,
                "messages": history[-2:]
            },
            timeout=2
        )
    except Exception as e:
        print(f"DEBUG ERROR: Failed to send to /conversation: {str(e)}", flush=True)
        logger.warning(f"Failed to send to /conversation: {e}")
    
    # Build TwiML response
    print("DEBUG: Building TwiML response", flush=True)
    response = VoiceResponse()
    response.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    redirect_url = f"{Config.APP_PUBLIC_GATHER_URL}?CallSid={unique_id}"
    response.redirect(redirect_url)

    # Initiate outbound call
    print(f"DEBUG: Initiating outbound call to {customer_phonenumber}", flush=True)
    call = client.calls.create(
        twiml=str(response),
        to=customer_phonenumber,
        from_=Config.TWILIO_FROM_NUMBER,
        method="GET",
        status_callback=Config.APP_PUBLIC_EVENT_URL,
        status_callback_method="POST"
    )
    print(f"DEBUG: Call initiated with SID: {call.sid}", flush=True)
    return jsonify({'message': 'Call initiated', 'call_sid': call.sid})


@app.route('/gather', methods=['GET', 'POST'])
def gather_input():
    """Gather speech input from the call"""
    call_sid = request.args.get('CallSid', '')
    print(f"DEBUG: Gathering speech input for call {call_sid}", flush=True)
    
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
    """Handle inbound calls and gather speech input"""
    print("DEBUG: Handling inbound call", flush=True)
    resp = VoiceResponse()
    unique_id = str(uuid.uuid4())
    print(f"DEBUG: Generated unique ID for inbound call: {unique_id}", flush=True)

    agent_response = initiate_inbound_message()
    print(f"DEBUG: Generated initial agent response for inbound call", flush=True)
    audio_data = text_to_speech(agent_response)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)
    print(f"DEBUG: Saved audio to {audio_file_path}", flush=True)

    resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))

    # Save initial inbound history
    history = [{"role": "assistant", "content": agent_response}]
    save_conversation(unique_id, history)
    
    # Post to conversation endpoint
    try:
        print(f"DEBUG: Posting initial inbound conversation to /conversation endpoint", flush=True)
        requests.post(
            "http://localhost:5000/conversation",
            json={
                "unique_id": unique_id,
                "messages": history
            },
            timeout=2
        )
    except Exception as e:
        print(f"DEBUG ERROR: Failed to send to /conversation: {str(e)}", flush=True)
        logger.warning(f"Failed to send to /conversation: {e}")

    resp.redirect(url_for('gather_input', CallSid=unique_id))
    return str(resp)


@app.route('/process-speech', methods=['POST'])
def process_speech():
    """Process speech input and generate AI response"""
    speech_result = request.values.get('SpeechResult', '').strip()
    call_sid = request.args.get('CallSid', '')
    
    print(f"DEBUG: Processing speech for call {call_sid}", flush=True)
    print(f"DEBUG: Speech result: {speech_result}", flush=True)

    history = load_conversation(call_sid)
    print(f"DEBUG: Loaded conversation history with {len(history)} messages", flush=True)

    print(f"DEBUG: Generating AI response", flush=True)
    ai_response_text = process_message(history, speech_result, call_sid)
    response_text = clean_response(ai_response_text)
    print(f"DEBUG: AI response generated: {response_text[:50]}...", flush=True)

    print(f"DEBUG: Converting AI response to speech", flush=True)
    audio_data = text_to_speech(response_text)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)
    print(f"DEBUG: Saved audio to {audio_file_path}", flush=True)

    resp = VoiceResponse()
    resp.play(url_for('serve_audio', filename=secure_filename(audio_filename), _external=True))
    
    if "<END_OF_CALL>" in ai_response_text:
        print(f"DEBUG: End of call detected, hanging up", flush=True)
        resp.hangup()
    else:
        print(f"DEBUG: Redirecting to gather more input", flush=True)
        resp.redirect(url_for('gather_input', CallSid=call_sid))

    # Update and persist history
    history.append({"role": "user", "content": speech_result})
    history.append({"role": "assistant", "content": response_text})
    save_conversation(call_sid, history)

    # Post to conversation endpoint
    try:
        print(f"DEBUG: Posting updated conversation to /conversation endpoint", flush=True)
        requests.post(
            "http://localhost:5000/conversation",
            json={
                "unique_id": call_sid,
                "messages": history[-2:]
            },
            timeout=2
        )
    except Exception as e:
        print(f"DEBUG ERROR: Failed to send to /conversation: {str(e)}", flush=True)
        logger.warning(f"Failed to send to /conversation: {e}")

    return str(resp)


@app.route('/event', methods=['POST'])
def event():
    """Handle call status events and trigger summarization for completed calls"""
    print("DEBUG: Entering event route", flush=True)
    call_status = request.values.get('CallStatus', '')
    call_sid = request.values.get('CallSid', '')
    unique_id = "1234567"
    print(f"DEBUG: Received event with CallStatus={call_status}, CallSid={call_sid}", flush=True)
    
    if call_status in ['completed', 'busy', 'failed'] and call_sid:
        print(f"DEBUG: Call {call_sid} ended with status: {call_status}", flush=True)
        
        # Only generate summary for completed calls
        if call_status == 'completed':
            print(f"DEBUG: Attempting to generate summary for completed call {call_sid}", flush=True)
            # Get the conversation history for this call
            message_history = load_conversation(unique_id)
            print(f"DEBUG: Loaded conversation history length: {len(message_history) if message_history else 0}", flush=True)
            
            if message_history:
                print(f"DEBUG: Starting summarization process for call {call_sid}", flush=True)
                try:
                    # Generate summary
                    summary_result = summariser(message_history, unique_id)
                    print(f"DEBUG: Summary generated successfully", flush=True)
                    
                    # Post to the /summary endpoint
                    try:
                        print(f"DEBUG: Posting summary to endpoint for call {unique_id}", flush=True)
                        post_resp = requests.post(
                            "http://localhost:5000/summary",
                            json={
                                "unique_id": unique_id,
                                "messages": summary_result
                            },
                            timeout=10
                        )
                        
                        print(f"DEBUG: Summary post response status: {post_resp.status_code}", flush=True)
                        if post_resp.status_code == 200:
                            print(f"DEBUG: Summary successfully posted to /summary endpoint", flush=True)
                        else:
                            print(f"DEBUG ERROR: Failed to post summary: {post_resp.status_code} - {post_resp.text}", flush=True)
                    except requests.exceptions.RequestException as e:
                        print(f"DEBUG ERROR: Request error posting summary: {str(e)}", flush=True)
                except Exception as e:
                    print(f"DEBUG ERROR: Error generating summary for call {call_sid}: {str(e)}", flush=True)
                    print(f"DEBUG ERROR: Exception type: {type(e)}", flush=True)
            else:
                print(f"DEBUG WARNING: No conversation history found for call {call_sid}", flush=True)
    
    print("DEBUG: Exiting event route", flush=True)
    return ('', 204)


@app.route('/conversation', methods=['POST'])
def receive_conversation():
    """Receive and store conversation messages"""
    print("DEBUG: Received conversation update", flush=True)
    data = request.json
    unique_id = data.get("unique_id")
    messages = data.get("messages", [])
    print(f"DEBUG: Conversation update for {unique_id} with {len(messages)} messages", flush=True)

    if not unique_id or not isinstance(messages, list):
        print("DEBUG ERROR: Invalid conversation format", flush=True)
        return jsonify({"error": "Invalid format"}), 400

    # Update conversation history
    if unique_id not in CONVERSATIONS:
        CONVERSATIONS[unique_id] = []
    CONVERSATIONS[unique_id].extend(messages)
    print(f"DEBUG: Updated in-memory conversation for {unique_id}, now has {len(CONVERSATIONS[unique_id])} messages", flush=True)

    return '', 204


@app.route('/conversation/<unique_id>', methods=['GET'])
def get_conversation_endpoint(unique_id):
    """Retrieve conversation history"""
    print(f"DEBUG: Getting conversation for {unique_id}", flush=True)
    conversation = CONVERSATIONS.get(unique_id, [])
    print(f"DEBUG: Retrieved conversation with {len(conversation)} messages", flush=True)
    return jsonify(conversation)


@app.route('/summary', methods=['POST'])
def receive_summary():
    """Receive and store a summary"""
    print("DEBUG: Received summary submission", flush=True)
    data = request.json
    unique_id = data.get("unique_id")
    messages = data.get("messages")
    print(f"DEBUG: Summary submission for {unique_id}", flush=True)
    
    if not unique_id:
        print("DEBUG ERROR: Missing unique_id in summary submission", flush=True)
        return jsonify({"error": "Missing unique_id"}), 400
    
    # Store the summary JSON object directly
    SUMMARIES[unique_id] = messages
    
    # Also save to file
    save_summary(unique_id, messages)
    
    print(f"DEBUG: Summary for call {unique_id} stored successfully", flush=True)
    logger.info(f"Summary for call {unique_id} received and stored")
    
    return jsonify({"status": "success"}), 200


@app.route('/summary/<unique_id>', methods=['GET'])
def get_summary(unique_id):
    """Retrieve a summary by call ID"""
    print(f"DEBUG: Getting summary for {unique_id}", flush=True)
    
    # First check in-memory store
    if unique_id in SUMMARIES:
        print(f"DEBUG: Retrieved summary from memory for call {unique_id}", flush=True)
        logger.info(f"Retrieved summary from memory for call {unique_id}")
        return jsonify(SUMMARIES.get(unique_id))
    
    # Then check file store
    summary = load_summary(unique_id)
    if summary:
        # Add to in-memory store for faster access next time
        SUMMARIES[unique_id] = summary
        print(f"DEBUG: Retrieved summary from file for call {unique_id}", flush=True)
        logger.info(f"Retrieved summary from file for call {unique_id}")
        return jsonify(summary)
    
    print(f"DEBUG WARNING: Summary not found for call {unique_id}", flush=True)
    logger.warning(f"Summary not found for call {unique_id}")
    return jsonify({"error": "Summary not found"}), 404


@app.route('/summary/<unique_id>', methods=['POST'])
def post_summary(unique_id):
    """Store a summary for a specific call ID"""
    print(f"DEBUG: Posting summary for {unique_id}", flush=True)
    data = request.json
    
    if not data:
        print("DEBUG ERROR: Missing summary data in POST request", flush=True)
        return jsonify({"error": "Missing summary data"}), 400
    
    # Store the summary JSON object directly
    SUMMARIES[unique_id] = data
    
    # Also save to file
    save_summary(unique_id, data)
    
    print(f"DEBUG: Summary for call {unique_id} posted and stored successfully", flush=True)
    logger.info(f"Summary for call {unique_id} posted and stored")
    
    return jsonify({"status": "success", "message": f"Summary for call {unique_id} stored successfully"}), 200


@app.route('/trigger-summary/<call_sid>', methods=['POST'])
def trigger_summary(call_sid):
    """Manually trigger summarization for a specific call"""
    print(f"DEBUG: Manually triggering summary for call {call_sid}", flush=True)
    message_history = load_conversation(call_sid)
    
    if not message_history:
        print(f"DEBUG ERROR: No conversation found for call {call_sid}", flush=True)
        return jsonify({"error": "Conversation not found"}), 404
    
    try:
        print(f"DEBUG: Starting manual summarization for call {call_sid}", flush=True)
        summary_result = summariser(message_history, call_sid)
        print(f"DEBUG: Manual summarization completed successfully", flush=True)
        return jsonify({"status": "success", "summary": summary_result}), 200
    except Exception as e:
        print(f"DEBUG ERROR: Error in manual summarization: {str(e)}", flush=True)
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({"error": "Failed to generate summary", "details": str(e)}), 500


if __name__ == '__main__':
    print("DEBUG: Starting Flask server on port 5000", flush=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
