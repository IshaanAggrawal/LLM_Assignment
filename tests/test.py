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
    """A custom handler to suppress standard HTTP logging to keep output clean."""
    def log_message(self, format, *args): 
        pass 

def start_file_server():
    """Starts a temporary file server to serve the JSON data files."""
    os.chdir(DATA_DIR) 
    with socketserver.TCPServer(("", FILE_SERVER_PORT), QuietHandler) as httpd:
        print(f"📁 File Server started at http://localhost:{FILE_SERVER_PORT}")
        httpd.serve_forever()

def test_conversation(chat_file: str, vector_file: str, target_turn: int):
    """Sends a single test case to the API and prints results."""
    chat_url = f"http://localhost:{FILE_SERVER_PORT}/chats/{chat_file}"
    vector_url = f"http://localhost:{FILE_SERVER_PORT}/vectors/{vector_file}"
    
    print(f"\n{'='*70}")
    print(f"🧪 Testing: {chat_file} (Turn {target_turn})")
    print(f"{'='*70}")
    
    payload = {
        "chat_url": chat_url,
        "vector_url": vector_url,
        "target_turn": target_turn
    }

    try:
        start_time = time.time()
        # Timeout set to 60s to allow for Tier 3 escalation if needed
        response = requests.post(API_URL, json=payload, timeout=60)
        eval_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS! (Total Test Time: {eval_time:.2f}s)")
            print(f"\n📊 RESULTS:")
            print(json.dumps(data, indent=2))
            
            # Additional check for the 'evaluator_model' field
            if "evaluator_model" in data:
                print(f"\nℹ️  Model used: {data['evaluator_model']}")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Main API is not running.") 
        print("   -> Run: uvicorn src.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def run_all_tests():
    """Main execution flow."""
    # 1. Start File Server in Background
    server_thread = threading.Thread(target=start_file_server, daemon=True)
    server_thread.start()
    time.sleep(1) # Wait for server to boot
    
    print("\n" + "="*70)
    print("🚀 BeyondChats LLM Evaluator - Comprehensive Test Suite")
    print("="*70)
    
    # 2. Define Test Cases
    test_cases = [
        {
            # CASE 1: The Hallucination (Subsidized Rooms)
            "chat_file": "sample-chat-conversation-01.json",
            "vector_file": "sample_context_vectors-01.json",
            "target_turn": 14,
            "description": "Hallucination Check (Turn 14: Subsidized Rooms)"
        },
        {
            # CASE 2: The Complex Question (Donor Eggs)
            "chat_file": "sample-chat-conversation-02.json",
            "vector_file": "sample_context_vectors-02.json",
            "target_turn": 15,
            "description": "Accuracy Check (Turn 15: Donor Egg Risks)"
        }
    ]
    
    # 3. Run Tests
    results = []
    for i, tc in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{len(test_cases)}: {tc['description']}")
        success = test_conversation(tc["chat_file"], tc["vector_file"], tc["target_turn"])
        results.append(success)
        time.sleep(1) # Brief pause between tests
    
    # 4. Final Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    passed = sum(results)
    print(f"✅ Passed: {passed}/{len(results)}")
    print(f"❌ Failed: {len(results) - passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! System is ready.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Check logs above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)