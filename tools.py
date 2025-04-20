import requests

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
    "calculate_discount": {
        "name": "calculate_discount",
        "description": "Calculates discount based on current sentiment score and maximum discount."
    },
    "summariser": {
        "name": "summariser",
        "description": "Fetches summary of the conversation and post it to the database in a json format.",
        
    }
}


# def fetch_product_price(arguments):
#     print('Fetch product Price is called')
#     return f"The price is $29 per month."


def fetch_product_db():



def calc_disc(product_name):    
   #llm call for score, response se max discount, based on that final discount.
    print('Calculating discount...')

    # # Step 1: Fetch the full product database
    # url = 'https://kno2getherworkflow.ddns.net/webhook/fetchMemberShip'
    # headers = {'Content-Type': 'application/json'}
    # response = requests.post(url, headers=headers, json={})

    # if response.status_code != 200:
    #     return "Failed to fetch product data."

    all_products = response.json()

    # Step 2: Find the specific product row
    product = next((item for item in all_products if item['title'].lower() == product_name.lower()), None)
    
    if not product:
        return "Product not found."

    price = product.get('price', 0)
    price = price*1000

    # Step 3: Call LLM to get sentiment score (stub below)
    client = genai.Client(api_key="AIzaSyCBwvcLQ4n5QrJ9Q3l28nyphMkXa0ucyjs")

    prompt = (
        "Given the conversation history, where a conversation between a salesperson and customer for laptops is given, calculate a sentiment score from 0 to 1 where 1 is the most likely to buy product, 0 is least likely. Return only and only sentiment score nothing else."
        f"Conversation History:\n{message_history}\n\n"
    )

    llm_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    sentiment_score_text = llm_response.text.strip()

    sentiment_score = float(sentiment_score_text)
    print(sentiment_score)

    # Step 4: Calculate discount
    offered_price = round((sentiment_score) * price, 2)

    print(offered_price)


def summariser(message_history):
     #Just before cutting the call, llm se json format usme de denge - Name, Contact, Product, Datetime, Sentiment, Sold/Not, Final Discount, Sold Price, short desc. POST
    print('Summarising the call...')

    # Step 1: Call Gemini LLM to get structured JSON summary
    client = genai.Client(api_key="AIzaSyCBwvcLQ4n5QrJ9Q3l28nyphMkXa0ucyjs")

    prompt = (
        "You are an AI assistant summarising a sales call.\n"
        "Given the full message history of a conversation, return a JSON summary with these fields:\n"
        "Customer Name, Contact, Product Name, Datetime, Sentiment (0 to 1), "
        "Sold/Not (Yes/No), Final Discount (%), Sold Price ($), "
        "Short Summary (2-3 lines about the call).\n\n"
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
    
    print(summary_json)