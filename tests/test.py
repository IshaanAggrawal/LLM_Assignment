import json
import requests
import os

API_URL = "http://localhost:8000/api/v1/evaluate"
DATA_DIR = "data"

def load_json(subfolder, filename):
    path = os.path.join(DATA_DIR, subfolder, filename)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {path} not found.")
        return None

def run_test():
    print("--- Starting Local Test ---")
    
    # 1. Load Data
    chat_data = load_json("chats", "sample-chat-conversation-01.json")
    vector_data = load_json("vectors", "sample_context_vectors-01.json")
    
    if not chat_data or not vector_data:
        return

    # 2. Setup Payload (Targeting Turn 14 - The Hallucination)
    turns = chat_data.get('chat_conversation', {}).get('conversation_turns', chat_data.get('conversation_turns', []))
    target_turn = 14
    
    context_texts = [item['text'] for item in vector_data['data']['vector_data']]
    
    # Extract Q&A pair
    user_q, ai_ans, u_time, a_time = "", "", "", ""
    for i, t in enumerate(turns):
        if t['turn'] == target_turn:
            ai_ans = t['message']
            a_time = t['created_at']
            user_q = turns[i-1]['message']
            u_time = turns[i-1]['created_at']
            break

    payload = {
        "conversation_id": chat_data.get('chat_id', 123),
        "user_query": user_q,
        "ai_response": ai_ans,
        "context_texts": context_texts,
        "user_timestamp": u_time,
        "ai_timestamp": a_time
    }

    # 3. Send to API
    print(f"Evaluating Turn {target_turn}...")
    try:
        res = requests.post(API_URL, json=payload)
        res.raise_for_status()
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    run_test()