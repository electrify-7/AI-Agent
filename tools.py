import requests
import google.generativeai as genai
import json
from connection import store_document

base_url = "https://small-dots-repair.loca.lt"

tools_info = {
    "fetch_product_db": {
        "name": "fetch_product_db",
        "description": "Fetches the complete database of products."
    },
    "prod_price": {
        "name": "prod_price",
        "description": "Fetches the price of products from the database",
        "parameters": {
            "product_name": ["Silver-Gym-Membership", "Gold-Gym-Membership", "Platinum-Gym-Membership"]
        }
    },
    "calc_disc": {
        "name": "calc_disc",
        "description": "Calculates discount based on current sentiment score and maximum discount."
    },
    "summariser": {
        "name": "summariser",
        "description": "Fetches summary of the conversation and post it to the database in a json format.",
        
    }
}


def get_products():
    url = f"{base_url}/laptopDetails"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch product data. Status code: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}



def onsite_appointment():
    # Assume arguments is a dict that contains date and time
    print('Onsite Appointment function is called')
    return f"Onsite Appointment is booked."

def save_call(message, customer_name, customer_contact):
    dataa = summariser(message)
    store_document(collection_name="summaryData", document={
        "name": customer_name,
        "contafct": customer_contact,
        "product": dataa.get("product"),
        "datetime": dataa.get("Datetime"),
        "sentiscore": dataa.get("sentiscore"),
        "sold" : dataa.get("sold"),
        "discount" : dataa.get("discount"),
        "soldprice" : dataa.get("soldprice"),
        "summary" : dataa.get("summary")
    })
    


def fetch_product_price(membership_type):
    return ""
#     print('Fetch product price is called')

#     # Set up the endpoint and headers
#     url = 'https://kno2getherworkflow.ddns.net/webhook/fetchMemberShip'
#     headers = {'Content-Type': 'application/json'}
    
#     # Prepare the data payload with the membership type
#     data = {
#         "membership": membership_type
#     }
    
#     # Send a POST request to the server
#     response = requests.post(url, headers=headers, json=data)
    
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse the JSON response to get the price
#         price_info = response.json()
#         return f"The price is ${price_info['price']} per month."
#     else:
#         return "Failed to fetch the price, please try again later."

def calendly_meeting():
    print('Calendly Meeting invite is sent.')
    # Assume arguments is a dict that contains date and time
    return f"Calendly meeting invite is sent now."

def appointment_availability():
    print('Checking appointment availability.')
    # Assume arguments is a dict that contains date and time
    return f"Our next available appointment is tomorrow, 24th April at 4 PM."


def fetch_product_db(membership_type):
    return ""
    
    

# def calc_disc(product_name, message_history):    
#    #llm call for score, response se max discount, based on that final discount.
#     #def calc_disc(product_name, history):
#     print('Calculating discount...')

#     # # Step 1: Fetch the full product database
    
#     url = f"{base_url}/laptopDetails"
#     headers = {'Content-Type': 'application/json'}
#     response = requests.get(url, headers=headers, json={})

#     if response.status_code != 200:
#         return "Failed to fetch product data."

#     all_products = response.json()

#     # Step 2: Find the specific product row
#     product = next((item for item in all_products if item['title'].lower() == product_name.lower()), None)
    
#     if not product:
#         return "Product not found."

#     price = product.get('price', 0)
#     price = price*1000

#     # Step 3: Call LLM to get sentiment score (stub below)
#    # client = genai.Client(api_key="AIzaSyCBwvcLQ4n5QrJ9Q3l28nyphMkXa0ucyjs")

#     prompt = (
#         "Given the conversation history, where a conversation between a salesperson and customer for laptops is given, calculate a sentiment score from 0 to 1 where 1 is the most likely to buy product, 0 is least likely. Return only and only sentiment score nothing else."
#         f"Conversation History:\n{message_history}\n\n"
#     )

#     llm_response = client.models.generate_content(
#         model="gemini-2.0-flash",
#         contents=prompt
#     )

#     sentiment_score_text = llm_response.text.strip()

#     sentiment_score = float(sentiment_score_text)
#     print(sentiment_score)

#     # Step 4: Calculate discount
#     offered_price = round((sentiment_score) * price, 2)

#     return offered_price


def summariser(message_history):
    # Step 1: Call Gemini LLM to get structured JSON summary
    client = genai.Client(api_key="AIzaSyCBwvcLQ4n5QrJ9Q3l28nyphMkXa0ucyjs")

    prompt = (
        "You are an AI assistant summarising a sales call.\n"
        "Given the full message history of a conversation, return a JSON summary with these fields:\n"
        "Customer Name, Contact, Product Name tagged as product, Datetime, Sentiment (0 to 1) tagged as sentiscore, "
        "Sold/Not tagged as sold (1/0), Final Discount tagged as discount (%), Sold Price tagged as soldprice ($), "
        "Short Summary tagged as summary(2-3 lines about the call).\n\n"
        f"Conversation History:\n{message_history}\n\n"
        "Respond in JSON format only."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    print(response)
    # Step 2: Parse the response text as JSON
    try:
      raw_text = response.text.strip()

      # Remove markdown code block syntax like ```json and ```
      if raw_text.startswith("```json"):
          raw_text = raw_text.replace("```json", "").strip()
      if raw_text.endswith("```"):
          raw_text = raw_text[:-3].strip()

    # Parse as JSON
      summary_json = json.loads(raw_text)

    except Exception as e:
      return f"Failed to parse summary JSON: {e}"
    
    
    store_document(collection_name="summaryData", document=summary_json)
    return summary_json


    