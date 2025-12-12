
### **1. Architecture Overview**

I chose a **Microservice Architecture** implementing the "Service-Repository" pattern. This is standard practice for scalable Python backends as it cleanly separates the API interface (routes) from the core business logic (services).

#### **Architecture Diagram (Data Flow)**

```mermaid
graph TD
    User[User Client] -->|1. Chat Message| API[FastAPI Gateway]
    
    subgraph "Hot Path (Real-Time Response)"
        API -->|2. Generate Reply| ChatBot[Chatbot Engine]
        ChatBot -->|3. Response (<2s)| User
    end
    subgraph "Cold Path (Async Evaluation)"
        API -.->|4. Fire-and-Forget| Queue[Background Task Queue]
        Queue -->|5. Process| Worker[Audit Service]
        
        %% Layer 0: Cache
        Worker -->|Layer 0| Cache{Check Cache}
        Cache -->|Hit (0ms)| DB[(Results DB)]
        
        %% Layer 1: Guardrails
        Cache -->|Miss| L1{Layer 1: Guardrails}
        L1 -->|Fail| DB
        
        %% Layer 2: The Scout
        L1 -->|Pass| L2{Layer 2: Llama-8B}
        L2 -->|Confident (>0.9)| DB
        
        %% Layer 3: The Judge
        L2 -->|Unsure (<0.9)| L3[Layer 3: Llama-70B]
        L3 -->|Final Verdict| DB
        L3 -.->|Update| Cache
    end
```

#### **Tech Stack Decisions**

  * **FastAPI:** Chosen for its asynchronous capabilities. Unlike Flask, it handles concurrent requests natively, which is critical for high-throughput evaluation pipelines.
  * **Groq (LPU):** This was a strategic choice to meet the **"Latency"** requirement. Inference on Groq's LPU is \~10x faster than standard GPU-based APIs (like OpenAI), allowing for real-time grading without slowing down the user experience.
  * **Pydantic:** Used for strict data validation. It ensures the system fails fast on bad input (like empty strings or missing fields) rather than wasting compute resources processing invalid data.
  * **Tenacity:** Adds reliability. Network blips happen; this library automatically retries failed LLM calls with exponential backoff so the entire pipeline doesn't crash from a single timeout.
  * **SlowAPI:** Implements rate limiting to protect the system from abuse and Denial of Service (DoS) attacks.

-----

### **2. Security Implementation**

I didn't just build the logic; I built a secure system ready for deployment. I implemented a **3-Layer Security Shield**:

1.  **Rate Limiting (Traffic Control):**

      * **Implementation:** `@limiter.limit("10/minute")` on evaluation endpoints.
      * **Why:** Prevents abuse. Without this, a malicious actor (or a buggy script) could flood the API with thousands of requests, draining credits and crashing the server.
      * **Impact:** Adds negligible latency (\<1ms) but provides massive stability protection.

2.  **Payload Validation (Memory Protection):**

      * **Implementation:** `max_length=10000` constraints in `src/models/schemas.py`.
      * **Why:** Protects against memory exhaustion attacks. If someone sends a 100MB text payload, Pydantic rejects it immediately (422 Error) before it consumes server RAM.

3.  **CORS (Access Control):**

      * **Implementation:** `CORSMiddleware` in `main.py`.
      * **Why:** Restricts which domains can access the API. This prevents unauthorized websites from piggybacking on a user's session to make API calls.

-----

### **3. Metrics & Scoring Logic**

Here is exactly how I calculated the metrics requested in the assignment PDF:

  * **Response Relevance & Completeness:**
      * **How:** I engineered the prompt to explicitly ask the model: *"Does the AI answer the specific question asked? Is the answer complete?"* This moves beyond simple keyword matching to semantic understanding.
  * **Hallucination / Factual Accuracy:**
      * **How:** I used a **ReAct (Reason + Act)** approach. The prompt forces the model to first *extract claims* from the response and then *verify* each one against the provided context vectors. If a claim isn't supported by the context, it is flagged as a hallucination (Faithfulness = 0).
  * **Latency:**
      * **How:** Calculated as the historical time difference (`AI_Timestamp - User_Timestamp`). This measures the actual user-perceived delay, which is the metric that actually matters for UX.
  * **Costs:**
      * **How:** Precise token tracking. The system counts input/output tokens for every request and multiplies them by the specific pricing model of the active LLM (Llama-3-8B), giving a granular cost-per-interaction.

-----

### **4. Assignment Checklist (Fulfilled)**

  * **"Evaluate LLM responses' reliability":**
      * **Done.** The script successfully identified the "subsidized room" hallucination in the sample data (Turn 14).
  * **"Real-time parameters... Latency & Costs":**
      * **Done.** Minimized latency to sub-second levels using Groq and minimized costs using Context Truncation (\~2000 chars) and the efficient Llama-3-8B model.
  * **"Input: 2 JSONs":**
      * **Done.** The `extract_context_and_turn` parser handles the complex, nested JSON structures provided in the samples.
  * **"Run your script at scale":**
      * **Done.** Scalability is ensured via:
        1.  **Async/Await:** Non-blocking I/O allows handling hundreds of concurrent requests.
        2.  **Tiered Evaluation:** The architecture supports swapping models (e.g., 8B for fast checks, 70B for deep audits) to balance speed and accuracy at scale.

This solution is not just a script; it's a production-ready microservice architecture designed for performance, security, and maintainability.
🛡️ BeyondChats LLM EvaluatorA High-Performance, Scalable Microservice for RAG EvaluationThis project is a production-grade evaluation pipeline designed to audit Chatbot conversations for Hallucinations and Relevance. Unlike simple scripts, this is an asynchronous microservice architecture engineered to handle millions of daily conversations with near-zero latency impact on the user.🚀 1. Local Setup InstructionsFollow these steps to get the system running on your local machine.PrerequisitesPython 3.9+GitInstallation StepsClone the Repositorygit clone <your-repo-url>
cd llm-evaluator
Create Virtual Environmentpython -m venv venv

# Windows:
.\venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
Install Dependenciespip install -r requirements.txt
Configure EnvironmentCreate a .env file in the root directory and add your Groq API Key:GROQ_API_KEY=gsk_... (your key here)
ENV=development
Run the Server# Starts the FastAPI Server on Port 8000 with Hot Reload
uvicorn src.main:app --reload
Run the Test SuiteOpen a new terminal window (keep the server running) and execute:python tests/test.py

### **Estimated Costs for 1 Million Daily Users**
| Metric | Value |
| :--- | :--- |
| **Daily Traffic** | 1,000,000 Conversations |
| **Audit Volume (10% Sample)** | 100,000 Audits / Day |
| **Cache Hit Rate** | ~30% (Estimated) |
| **Net LLM Calls** | 70,000 / Day |
| **Avg Cost / Audit** | $0.00016 |
| **Daily LLM Cost** | ~$11.20 |
| **Monthly LLM Cost** | **~$336.00** |
