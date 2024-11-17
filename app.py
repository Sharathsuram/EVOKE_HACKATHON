from flask import Flask, send_from_directory
import os
from integrated_parser import IntegratedEmailSystem  # Assuming your script is named IntegratedEmailSystem.py

# Create Flask app
app = Flask(__name__)

# Define the directory where the HTML file will be stored
HTML_DIR = os.path.abspath(".")  # Current directory
HTML_FILE = "latest_email.html"

@app.route("/")
def welcome():
    """Welcome endpoint"""
    return {
        "message": "Welcome to the Email Processing API!",
        "endpoints": {
            "get_latest_email": "/latest-email"
        }
    }

@app.route("/latest-email", methods=["GET"])
def get_latest_email():
    """Serve the latest email HTML file"""
    if os.path.exists(os.path.join(HTML_DIR, HTML_FILE)):
        return send_from_directory(HTML_DIR, HTML_FILE)
    else:
        return {"error": "No processed email available yet."}, 404

if __name__ == "__main__":
    # Start the email processing system in a separate thread
    import threading

    def start_email_processing():
        system = IntegratedEmailSystem()
        system.run_continuous_processing()

    # Start email processing in a thread
    email_thread = threading.Thread(target=start_email_processing)
    email_thread.daemon = True
    email_thread.start()

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)
