import requests
import json
from google import genai
tools_info = {
    "calc_disc": {
        "name": "calc_disc",
        "description": "Calculates discount based on current sentiment score and maximum discount.",
        "parameters": {
            "product_name": []
        }
    },
    "summariser": {
        "name": "summariser",
        "description": "Fetches summary of the conversation and post it to the database in a json format.",
        
    }
}



def calc_disc(message_history,product_name):    
    print('Calculating discount...')

    # # Step 1: Fetch the full product database
    # url = 'https://kno2getherworkflow.ddns.net/webhook/fetchMemberShip'
    # headers = {'Content-Type': 'application/json'}
    # response = requests.post(url, headers=headers, json={})

    # if response.status_code != 200:
    #     return "Failed to fetch product data."

    # Step 3: Call LLM to get sentiment score (stub below)
    client = genai.Client(api_key="AIzaSyCBwvcLQ4n5QrJ9Q3l28nyphMkXa0ucyjs")

    prompt = (
        "Given the conversation history, where a conversation between a salesperson and customer for laptops is given, calculate a sentiment score from 0 to 1 where 1 is the most likely to buy product, 0 is least likely. Return only and only sentiment score nothing else."
        f"Conversation History:\n{message_history}\n\n"
    )

    prompt2 = (
       "Take the laptop database from message history - \n{message_history}\n. From this take the max_discount in percentage and return as int. Return only the integer max discount."
    )
    llm_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    llm_response2 = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt2
    )

    sentiment_score_text = llm_response.text.strip()

    sentiment_score = float(sentiment_score_text)
    print(sentiment_score)
    max_disc_text = llm_response2.text.strip()

    max_discount = int(max_disc_text)
    # Step 4: Calculate discount
    offered_discount = max_discount*(1-sentiment_score)
    return offered_discount



def summariser(message_history):
    print('Summarising the call...')
    client = genai.Client(api_key="AIzaSyCDRGVamqQ64AgaWdfNndPQRzCt31NY9qE")
    prompt = (
        'You are an AI assistant that summarizes sales call conversations. Given the entire conversation history between a sales agent and a customer, generate a structured JSON summary using the following fields: userid: user id given in history. callid: call id given in history. datetime: the time given in conversation_history. discount: 15.0 — the percentage discount given. name: "Alice Johnson" — the full name of the customer. product_name: "SuperCRM Pro" — the product discussed or sold. sentiment_score: 0.75 — a value from 0 to 1 indicating customer sentiment. shortDescription: "Converted to Pro plan with 15% discount." — a short summary of the call outcome. sold: 1 — use 1 if the product was sold, else 0. soldPrice: 849.99 — the final price paid by the customer. contactno: Given in message history'
        f"Conversation History:\n{message_history}\n\n"
        "Respond in JSON format only. Use the conversation history to generate the JSON response. and donot include any other thing, just json use _ wherever required"
    )
    llm_resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    raw = llm_resp.text.strip()
    # Clean up code fences
    if raw.startswith(''):
        raw = raw.split('')[-2]
    summary_json = json.loads(raw)

    # Store in database via backend
    store_document(collection_name="summaryData", document=summary_json)

    # POST to /summary endpoint on local server
    post_resp = requests.post("http://localhost:5000/summary", json=summary_json)
    if post_resp.status_code == 200:
        print("Summary successfully posted to /summary.")
    else:
        print(f"Failed to post summary: {post_resp.status_code} - {post_resp.text}")

    return summary_json