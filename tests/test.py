import threading
import http.server
import socketserver
import requests
import time
import json
import os

API_URL = "http://localhost:8000/api/v1/evaluate/batch-url"
FILE_SERVER_PORT = 9000
DATA_DIR = "data" 

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass 

def start_file_server():
    """Starts a temporary HTTP server serving the 'data' directory"""
    os.chdir(DATA_DIR) 
    with socketserver.TCPServer(("", FILE_SERVER_PORT), QuietHandler) as httpd:
        print(f"📂 Temporary File Server started at port {FILE_SERVER_PORT}...")
        httpd.serve_forever()

def run_simulation():
    # 1. Start File Server in Background Thread
    server_thread = threading.Thread(target=start_file_server, daemon=True)
    server_thread.start()
    time.sleep(1) 

    # 2. Construct the "Fake" URLs
    chat_url = f"http://localhost:{FILE_SERVER_PORT}/chats/sample-chat-conversation-02.json"
    vector_url = f"http://localhost:{FILE_SERVER_PORT}/vectors/sample_context_vectors-02.json"

    print(f"\n🔗 Testing Link Evaluation Route...")
    print(f"Chat Link:   {chat_url}")
    print(f"Vector Link: {vector_url}")

    # 3. Call the API
    payload = {
        "chat_url": chat_url,
        "vector_url": vector_url
    }

    try:
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! The API downloaded and processed the links.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\n❌ FAILED with code {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Main API (port 8000) is not running.")

if __name__ == "__main__":
    if not os.path.exists("data"):
        print("Error: Run this script from the project root (where 'data' folder is).")
    else:
        run_simulation()