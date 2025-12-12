import requests
import os
import json

# Configuration
API_URL = "http://localhost:8000/api/v1/evaluate/batch"
CHAT_PATH = "data/chats/sample-chat-conversation-01.json"
VECTOR_PATH = "data/vectors/sample_context_vectors-01.json"

def run_batch_test():
    # 1. Verify files exist
    if not os.path.exists(CHAT_PATH) or not os.path.exists(VECTOR_PATH):
        print("Error: Could not find data files.")
        print(f"Checked: {CHAT_PATH}")
        print(f"Checked: {VECTOR_PATH}")
        return

    print(f"--- Uploading Batch Files to {API_URL} ---")
    print(f"Chat File:   {CHAT_PATH}")
    print(f"Vector File: {VECTOR_PATH}")

    # 2. Prepare the files for upload
    # We open them in binary mode ('rb') to ensure safe transmission
    files = {
        'chat_file': ('chat.json', open(CHAT_PATH, 'rb'), 'application/json'),
        'vector_file': ('vectors.json', open(VECTOR_PATH, 'rb'), 'application/json')
    }

    try:
        # 3. Send POST request
        response = requests.post(API_URL, files=files)
        
        # 4. Handle Response
        if response.status_code == 200:
            print("\n✅ Success! Evaluation Result:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\n❌ Error {response.status_code}:")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Failed. Is the server running?")
        print("Run: uvicorn src.main:app --reload")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
    finally:
        # Always close file handles
        files['chat_file'][1].close()
        files['vector_file'][1].close()

if __name__ == "__main__":
    run_batch_test()