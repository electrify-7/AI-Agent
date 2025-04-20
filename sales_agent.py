import asyncio
import base64
import json
import os
import subprocess
import tempfile
import numpy as np
from scipy.io.wavfile import write
import sounddevice as sd
from pynput import keyboard
from faster_whisper import WhisperModel
import pygame
from termcolor import colored
import websockets
import anthropic
import openai
import logging
from openai import AsyncOpenAI
from groq import Groq

# Define API keys and voice ID
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('VOICE_ID')

class FasterWhisperTranscriber:
    def __init__(self, model_size="large-v3", sample_rate=44100):
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.model = WhisperModel(model_size, device="cuda", compute_type="float16")
        self.is_recording = False

    def on_press(self, key):
        if key == keyboard.Key.space:
            if not self.is_recording:
                self.is_recording = True
                print("Recording started.")
    
    def on_release(self, key):
        if key == keyboard.Key.space:
            if self.is_recording:
                self.is_recording = False
                print("Recording stopped.")
                return False

    def record_audio(self):
        recording = np.array([], dtype='float64').reshape(0, 2)
        frames_per_buffer = int(self.sample_rate * 0.1)
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            while True:
                if self.is_recording:
                    chunk = sd.rec(frames_per_buffer, samplerate=self.sample_rate, channels=2, dtype='float64')
                    sd.wait()
                    recording = np.vstack([recording, chunk])
                if not self.is_recording and len(recording) > 0:
                    break
            listener.join()
        return recording

    def save_temp_audio(self, recording):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        write(temp_file.name, self.sample_rate, recording)
        return temp_file.name
    
    def transcribe_audio(self, file_path):
        segments, info = self.model.transcribe(file_path, beam_size=5)
        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
        full_transcription = ""
        for segment in segments:
            print(segment.text)
            full_transcription += segment.text + " "
        os.remove(file_path)
        return full_transcription, info  

    # def transcribe_audio(self, file_path):
    #     segments, info = self.model.transcribe(file_path, beam_size=5)
    #     print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    #     full_transcription = ""
    #     for segment in segments:
    #         print(segment.text)
    #         full_transcription += segment.text + " "
    #     os.remove(file_path)
    #     return full_transcription


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Set OpenAI API key
gclient = Groq(api_key='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')

# def is_installed(lib_name):
#     return shutil.which(lib_name) is not None


async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""

    async for text in chunks:
        if text is None:  # Check if text is None and continue to the next iteration if so
            continue

        if buffer.endswith(tuple(splitters)):
            yield buffer + " "
            buffer = text
        elif text.startswith(tuple(splitters)):
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        yield buffer + " "



async def stream(audio_stream):
    """Stream audio data using mpv player."""
    # if not is_installed("mpv"):
    #     raise ValueError(
    #         "mpv not found, necessary to stream audio. "
    #         "Install instructions: https://mpv.io/installation/"
    #     )

    mpv_process = subprocess.Popen(
        ["mpv", "--no-cache", "--no-terminal", "--", "fd://0"],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    print("Started streaming audio")
    async for chunk in audio_stream:
        if chunk:
            mpv_process.stdin.write(chunk)
            mpv_process.stdin.flush()

    if mpv_process.stdin:
        mpv_process.stdin.close()
    mpv_process.wait()


async def text_to_speech_input_streaming(voice_id, text_iterator):
    """Send text to ElevenLabs API and stream the returned audio."""
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "xi_api_key": ELEVENLABS_API_KEY,
        }))

        async def listen():
            """Listen to the websocket for audio data and stream it."""
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break

        listen_task = asyncio.create_task(stream(listen()))

        async for text in text_chunker(text_iterator):
            await websocket.send(json.dumps({"text": text, "try_trigger_generation": True}))

        await websocket.send(json.dumps({"text": ""}))

        await listen_task


# async def chat_completion(query):
#     """Retrieve text from OpenAI and pass it to the text-to-speech function."""
#     response = await aclient.chat.completions.create(model='gpt-3.5-turbo', messages=[{'role': 'user', 'content': query}],
#     temperature=1, stream=True)

#     async def text_iterator():
#         async for chunk in response:
#             delta = chunk.choices[0].delta
#             yield delta.content

#     await text_to_speech_input_streaming(VOICE_ID, text_iterator())

async def handle_recording():
    whisper = FasterWhisperTranscriber()
    english_system_message  = {
            "role": "system",
            "content": """Your name is Sally. You are a Sales Representative working at ByteMe, a company that offers a wide variety of high-performance laptops tailored for students, professionals, businesses, and gamers. Your role is to contact potential customers over phone calls and assist them in finding the right laptop based on their specific needs and help them confirm their order. You are an AI Assistant, and you begin the call with a friendly greeting and introduction, making it clear you're here to help them choose the perfect laptop. Do not mention the contact form unless the prospect specifically asks about how you got their information.

Your primary goal during the call is to guide the customer toward confirming a purchase. Keep your responses short and clear to maintain their attention. Focus on understanding the customer's use case, preferences, and budget before recommending a suitable laptop. Never assume what they need—instead, always confirm your understanding of their requirements. Use a helpful and conversational tone, and avoid technical jargon unless the customer asks for it. Once their needs are clear, confidently suggest a laptop option and aim to close the order.

When the conversation is over, always end by saying: "Hope you have a good day."
Always and you MUST think about at WHICH CONVERSATION STAGE you are at, before answering SPECIFIC and RELEVANT to that CONVERSATION STAGE:

"1": "Introduction: Start the conversation by introducing yourself and your company. Be polite and respectful while keeping the tone of the conversation professional. Your greeting should be welcoming. Always clarify in your greeting the reason why you are calling.",
"2": "Qualification: Qualify the prospect by confirming if they are the right person to talk to regarding your product/service. Ensure that they have the authority to make purchasing decisions.",
"3": "Value proposition: Briefly explain how your product/service can benefit the prospect. Focus on the unique selling points and value proposition of your product/service that sets it apart from competitors.",
"4": "Needs analysis: Ask open-ended questions to uncover the prospect's needs and pain points. Listen carefully to their responses and take notes.",
"5": "Solution presentation: Based on the prospect's needs, present your product/service as the solution that can address their pain points.",
"6": "Objection handling: Address any objections that the prospect may have regarding your product/service. Be prepared to provide evidence or testimonials to support your claims. If pricing is a concern, you may offer a limited-time discount to help overcome the objection and move the conversation forward.",
"7": "Close: Ask for the sale by proposing a next step. This could be a demo, a trial or a meeting with decision-makers. Ensure to summarize what has been discussed and reiterate the benefits.",
"8": "End conversation: It's time to end the call as there is nothing else to be said."
            """
        }





    while True:
        try:
            print("\nPress and hold the spacebar to start recording...")
            recording = whisper.record_audio()
            file_path = whisper.save_temp_audio(recording)
            full_transcript, info = whisper.transcribe_audio(file_path)
                        # Select the system message based on detected language
            
            message_history = [english_system_message]

            message_history.append({"role": "user", "content": full_transcript})
            # Take user input from the terminal instead of recording audio
            # user_input = input("\nEnter your message (or type 'exit' to quit): ")
            # if user_input.lower() == 'exit':
            #     print("\nExiting...")
            #     break
            
            # message_history.append({"role": "user", "content": user_input})
            
            response = gclient.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=message_history,
                temperature=0.5,
                max_tokens=200,
                stream=False,
                top_p=1
            ) 

            assistant_response = ""

            async def text_iterator():
                async for chunk in response:
                    delta_content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                    print(colored(delta_content, "green"), end="", flush=True)
                    nonlocal assistant_response
                    assistant_response += delta_content
                    # logging.info(delta_content)
                    yield delta_content
            
            try:
                await text_to_speech_input_streaming(VOICE_ID, text_iterator())
            except asyncio.CancelledError:
                pass

            message_history.append({"role": "assistant", "content": assistant_response})

        except KeyboardInterrupt:
            print("\nExiting due to KeyboardInterrupt...")
            break


# Main execution
if __name__ == "__main__":
    asyncio.run(handle_recording())


