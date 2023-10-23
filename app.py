from flask import Flask, render_template
import os
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)

# Ensure the log directory exists
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, "stock_data4.log")
logging.basicConfig(filename=log_file, level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Construct the MongoDB connection URI
uri = "mongodb+srv://pranjal1476772:Pj%401476772@cluster0.cfozvcv.mongodb.net/?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = MongoClient(uri)

# Check the MongoDB connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    logging.error(f"{e}")

# Create or get the collection
db = client["ICICIBANK_data"]
collection_name = "ICICIBANK_data_15min"

if collection_name not in db.list_collection_names():
    db.create_collection(collection_name)

collection = db[collection_name]

def collect_and_store_stock_data():
    try:
        # Get the current date and time
        now = datetime.now()

        # Check if the current time is within the collection window (11:00 AM to 2:00 PM)
        if now.time() < datetime.strptime('11:00', '%H:%M').time() or now.time() > datetime.strptime('14:00', '%H:%M').time():
            print("Data collection is outside the specified time window.")
            return

        print("Fetching and storing data...")

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

def visualize_data(collection):
    # Retrieve data from MongoDB
    data = list(collection.find().sort("_id", 1))  # Sort by date in ascending order

    if not data:
        print("No data available for visualization.")
        return

    # Extract timestamps and corresponding data
    timestamps = [entry["_id"] for entry in data]

    # Extract relevant data for visualization (e.g., 'Open', 'High', 'Low', 'Close')
    open_prices = [entry["Open"] for entry in data]
    high_prices = [entry["High"] for entry in data]
    low_prices = [entry["Low"] for entry in data]
    close_prices = [entry["Close"] for entry in data]

    # Generate a sample plot (replace with your data and Matplotlib code)
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.plot(timestamps, open_prices, label='Open', color='green')
    ax.plot(timestamps, high_prices, label='High', color='blue')
    ax.plot(timestamps, low_prices, label='Low', color='red')
    ax.plot(timestamps, close_prices, label='Close', color='black')

    # Save the plot as an image file
    plot_filename = 'static/plots/plot.png'
    canvas = FigureCanvas(fig)
    canvas.print_figure(plot_filename, format='png')

    return plot_filename

@app.route('/')
def index():
    plot_filename = visualize_data(collection)
    return render_template('index.html', plot_filename=plot_filename)

if __name__ == '__main__':
    # Create a scheduler to run the function every 15 minutes
    scheduler = BackgroundScheduler()

    # Schedule the job to start and run every 15 minutes during the specified time window
    scheduler.add_job(collect_and_store_stock_data, 'interval', minutes=15, start_date=datetime.now().replace(hour=11, minute=0, second=0, microsecond=0), end_date=datetime.now().replace(hour=14, minute=0, second=0, microsecond=0))

    scheduler.start()

    # Run the Flask application
    app.run(debug=True)
