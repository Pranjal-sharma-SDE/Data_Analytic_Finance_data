import yfinance as yf
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

# Ensure the log directory exists
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, "stock_data4.log")
logging.basicConfig(filename=log_file, level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



# Construct the MongoDB connection URI

uri = os.getenv("MONGODB_URI")

# Create a new client and connect to the server
client = MongoClient(uri)  # No need for ServerApi unless you have specific requirements

# Check the MongoDB connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    logging.error(f"{e}")

# Create or get the collection (Replace with your actual database and collection names)
db = client["ICICIBANK_data"]
collection_name = "ICICIBANK_data_15min"

if collection_name not in db.list_collection_names():
    db.create_collection(collection_name)

collection = db[collection_name]

def collect_and_store_stock_data():
    try:
        print("Fetching and storing data...")
        # Get the current date and time
        now = datetime.now()

        # Check if the data has already been collected for the current minute
        last_record = collection.find_one(sort=[("_id", -1)])
        if last_record and last_record["_id"].minute == now.minute:
            print("Data has already been collected for this minute.")
            return

        # Create a Yahoo Finance Ticker instance
        ticker = "ICICIBANK.NS"
        icici_bank = yf.Ticker(ticker)

        # Get the historical data for the 15-minute interval
        icici_data = icici_bank.history(period="15m")

        # Store the data in MongoDB
        data_dict = icici_data.to_dict(orient="split")
        data_dict["_id"] = now
        collection.insert_one(data_dict)
        print(f"Stored data for {now}")
    except Exception as e:
        logging.error(f"An error occurred while fetching and storing data: {str(e)}")

# Create a scheduler to run the function every 15 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(collect_and_store_stock_data, 'interval', minutes=15)
scheduler.start()

try:
    # Keep the program running until interrupted
    print("Data collection has started. Press Ctrl+C to stop.")
    while True:
        pass
except KeyboardInterrupt:
    # Shutdown the scheduler and close the MongoDB client on interruption
    scheduler.shutdown()
    if client:
        client.close()
    print("Data collection stopped.")
