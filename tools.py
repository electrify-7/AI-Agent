import requests
import json
from google import genai
from groq import Groq

tools_info = {
    # "calc_disc": {
    #     "name": "calc_disc",
    #     "description": "Calculates discount based on current sentiment score and maximum discount.",
    #     "parameters": {
    #         "product_name": [ "XPS 13", "MacBook Air M2", "Spectre x360", "ThinkPad X1 Carbon Gen 11", "ROG Zephyrus G14", "Swift X 14"]
    #     }
    # },
    "summariser": {
        "name": "summariser",
        "description": "Fetches summary of the conversation and post it to the database in a json format.",
        
    }
}



# def calc_disc(message_history,product_name):    
#     print('Calculating discount...')

#     # # Step 1: Fetch the full product database
#     # url = 'https://kno2getherworkflow.ddns.net/webhook/fetchMemberShip'
#     # headers = {'Content-Type': 'application/json'}
#     # response = requests.post(url, headers=headers, json={})

#     # if response.status_code != 200:
#     #     return "Failed to fetch product data."

#     # Step 3: Call LLM to get sentiment score (stub below)
#     gclient = Groq(api_key='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')
#     prompt = (
#         "Given the conversation history, where a conversation between a salesperson and customer for laptops is given, calculate a sentiment score from 0 to 1 where 1 is the most likely to buy product, 0 is least likely. Return only and only sentiment score nothing else."
#         f"Conversation History:\n{message_history}\n\n"
#     )

#     prompt2 = (
#        "Take the laptop database from message history - \n{message_history}\n. From this take the max_discount in percentage and return as int. Return only the integer max discount."
#     )

#     llm_response = gclient.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 messages=prompt,
#                 temperature=0.5,
#                 max_tokens=4000,
#                 stream=False,
#                 top_p=1
#             )    

#     gclient2 = Groq(api_key='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')

#     llm_response2 = gclient2.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 messages=prompt2,
#                 temperature=0.5,
#                 max_tokens=4000,
#                 stream=False,
#                 top_p=1
#             )  

#     sentiment_score_text = llm_response.text.strip()

#     sentiment_score = float(sentiment_score_text)
#     print(sentiment_score)
#     max_disc_text = llm_response2.text.strip()

#     max_discount = int(max_disc_text)
#     # Step 4: Calculate discount
#     offered_discount = max_discount*(1-sentiment_score)
#     return offered_discount



def summariser(message_history, call_sid):
    print('Summarising the call...')
    gclient3 = Groq(api_key='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')
    
    # Properly format the messages parameter as an array of message objects
    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant that summarizes sales call conversations. Generate a structured JSON summary using specific fields."
        },
        {
            "role": "user",
            "content": f"Given the entire conversation history between a sales agent and a customer, generate a structured JSON summary using the following fields: userid: user id given in history. callid: call id given in history. datetime: the time given in conversation_history. discount: 15.0 — the percentage discount given. name: \"Alice Johnson\" — the full name of the customer. product_name: \"SuperCRM Pro\" — the product discussed or sold. sentiment_score: 0.75 — a value from 0 to 1 indicating customer sentiment. shortDescription: \"Converted to Pro plan with 15% discount.\" — a short summary of the call outcome. sold: 1 — use 1 if the product was sold, else 0. soldPrice: 849.99 — the final price paid by the customer. contactno: Given in message history\n\nConversation History:\n{message_history}\n\nRespond in JSON format only. Use the conversation history to generate the JSON response. Do not include any other thing, just JSON. Use _ wherever required."
        }
    ]
    
    try:
        llm_resp = gclient3.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.5,
            max_tokens=4000,
            stream=False,
            top_p=1
        )
        
        raw = llm_resp.choices[0].message.content.strip()
        
        # Clean up code fences if present
        if raw.startswith('```'):
            raw = raw[7:]
        elif raw.startswith('```'):
            raw = raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
            
        raw = raw.strip()
        summary_json = json.loads(raw)

        # POST to /summary endpoint on local server
        try:
            post_resp = requests.post(
                "http://localhost:5000/summary",
                json={
                    "unique_id": call_sid,
                    "messages": summary_json
                },
                timeout=10  # Add timeout to prevent hanging
            )
            
            if post_resp.status_code == 200:
                print("Summary successfully posted to /summary.")
            else:
                print(f"Failed to post summary: {post_resp.status_code} - {post_resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            print("Make sure the Flask server is running on http://localhost:5000")
        
        return summary_json
        
    except Exception as e:
        print(f"Error processing summary: {str(e)}")
        return {"error": "Processing error", "details": str(e)}



from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store: one summary per callid
SUMMARIES = {}  # { callid: summary_dict }

@app.route('/summary', methods=['POST'])
def receive_summary():
    data = request.json
    unique_id = data.get("unique_id")
    messages = data.get("messages")
    
    if not unique_id:
        return jsonify({"error": "Missing unique_id"}), 400
    
    # Store the summary JSON object directly
    SUMMARIES[unique_id] = messages
    
    return jsonify({"status": "success"}), 200

@app.route('/summary/<unique_id>', methods=['GET'])
def get_summary(unique_id):
    if unique_id not in SUMMARIES:
        return jsonify({"error": "Summary not found"}), 404
    return jsonify(SUMMARIES.get(unique_id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



