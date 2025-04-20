import os
from pymongo import MongoClient
from flask import Flask, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS

import os


load_dotenv()

# don't change these ( ip address I'll give)
MONGO_URI = os.environ.get("MONGO_URI")
DATABASE_NAME = os.environ.get("DATABASE_NAME")

# Setup the MongoDB client and database
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]


app = Flask(__name__)
CORS(app)

####### front end ke liye ONLY ##########
@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "Flask + MongoDB Atlas is running!"})

@app.route("/laptopDetails", methods=["GET"])
def get_laptopdetails():
    try:
        laptop_docs = list(db.laptopDetails.find())
        for doc in laptop_docs:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
        return jsonify(laptop_docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/callData", methods=["GET"])
def get_calldata():
    try:
        laptop_docs = list(db.callData.find())
        for doc in laptop_docs:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
        return jsonify(laptop_docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/customerData", methods=["GET"])
def get_customerdata():
    try:
        laptop_docs = list(db.customerData.find())
        for doc in laptop_docs:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
        return jsonify(laptop_docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/summaryData", methods=["GET"])
def get_summarydata():
    try:
        laptop_docs = list(db.summaryData.find())
        for doc in laptop_docs:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
        return jsonify(laptop_docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def get_document_by_tag(collection_name: str, tag: str, value):
    """
    Retrieve a single document from a collection where the field (tag) matches the specified value.
    """
    collection = db[collection_name]
    return collection.find_one({tag: value})


def store_document(collection_name: str, document: dict):
    """
    Insert a new document into the specified collection.
    Returns the inserted document's id.
    """
    collection = db[collection_name]
    result = collection.insert_one(document)
    return result.ierted_id



# Example Usage ( reference ke liye )
# if __name__ == "__main__":
#     # Example document from the "customer" collection
#     customer_doc = {
#         "name": "John Doe",
#         "email": "john@example.com",
#         "contactno": "1234567890",
#         "last_call_summary": "Followed up on recent enquiry."
#     }

#     # Store the customer document
#     customer_id = store_document("customer", customer_doc)
#     print(f"Inserted customer with id: {customer_id}")

#     # Retrieve a customer by email
#     customer = get_document_by_tag("customer", "email", "john@example.com")
#     print("Retrieved customer:", customer)


if __name__ == "__main__":
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    finally:
        client.close()