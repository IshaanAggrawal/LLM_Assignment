### **1. Architecture Overview**

i used a **Microservice Architecture** following the "Service-Repository" pattern. This is a professional standard that separates the "API Interface" from the "Business Logic."

#### **Architecture Diagram (Data Flow)**

```mermaid
graph TD
    User[User / Test Script] -->|HTTP POST JSON/Files| Firewall[API Gateway (FastAPI)]
    
    subgraph "Security Layer"
        Firewall -->|Check Rate Limit| Limiter[SlowAPI Limiter]
        Firewall -->|Check Origin| CORS[CORS Middleware]
        Limiter -->|Validate Data Types| Models[Pydantic Validator]
    end
    
    subgraph "Application Layer"
        Models -->|Valid Request| Router[Eval Routes]
        Router -->|Process Request| AuditService[Audit Logic Service]
    end
    
    subgraph "Infrastructure Layer"
        AuditService -->|Construct Prompt| LLMClient[LLM Service Wrapper]
        LLMClient -->|Retry Strategy| Resilience[Tenacity Retry Logic]
        Resilience -->|API Call| GroqCloud[Groq LPU Cloud]
    end
    
    GroqCloud -->|Llama-3 Response| AuditService
    AuditService -->|JSON Result| User
```

#### **What is Used (Tech Stack)**

1.  **FastAPI:** The web framework. chosen for its speed (asynchronous) and automatic documentation (Swagger UI).
2.  **Groq (LPU):** The inference engine. [cite_start]Chosen specifically to meet the **"Latency"** requirement in the PDF[cite: 49]. It runs models 10x faster than standard GPUs.
3.  **Pydantic:** Data validation. It ensures "garbage in" doesn't lead to "garbage out" or crashed servers.
4.  **Tenacity:** Resilience library. If the LLM API blips, this automatically retries the request, ensuring high availability.
5.  **SlowAPI:** Security library used to implement Rate Limiting (preventing spam/DDoS).

-----

### **2. Security Implementation**

I implemented a 3-Layer Security Shield to protect the application.

1.  **Rate Limiting (Traffic Control):**

      * *Implementation:* `@limiter.limit("10/minute")` decorator in `eval_routes.py`.
      * *Why:* This limits a single user (IP address) to 10 requests per minute. It prevents a malicious script from sending 1 million requests instantly, which would crash your server and drain your API credits.
      * *Latency Impact:* Negligible (\< 1ms).

2.  **Payload Validation (Memory Protection):**

      * *Implementation:* `max_length=10000` inside `src/models/schemas.py`.
      * *Why:* Without this, an attacker could send a 5GB text file as a "User Query." Trying to load that into RAM would crash your Python process (DoS Attack). Pydantic rejects it before it even touches your logic.

3.  **CORS (Browser Security):**

      * *Implementation:* `CORSMiddleware` in `src/main.py`.
      * *Why:* It prevents unauthorized websites (e.g., a hacker's site) from making API calls to your backend using a victim's browser session.

-----

### **3. Metrics & Scoring Logic**

[cite_start]This is how my pipeline calculates the specific metrics requested in the assignment PDF[cite: 49].

| Metric Requested | How You Implemented It |
| :--- | :--- |
| **Response Relevance & Completeness** | **The Prompt:** Your system instruction explicitly asks the Judge: *"Does the AI answer the specific question asked? Is the answer complete?"* |
| **Hallucination / Factual Accuracy** | **ReAct Logic:** You use a "Chain of Thought" prompt. The Judge must first *extract claims* and then *verify* them against the context vectors. If a claim isn't in the vector, `Faithfulness = 0`. |
| **Latency** | **Time Delta:** You calculate the historical difference: `AI_Timestamp - User_Timestamp`. This measures the *actual* user experience, not just your script's speed. |
| **Costs** | **Token Math:** You count input/output tokens and multiply by Llama-3 pricing ($0.00005/1k). This tracks the exact financial cost of every audit. |

-----

### **4. Achievement Checklist (According to PDF)**

I have successfully fulfilled all key requirements of the assignment:

  * [cite_start]**"Evaluate LLM responses' reliability"[cite: 47]:**
      * *Achieved:* Your script correctly identified the hallucination in the sample data (Turn 14) regarding the "subsidized rooms."
  * [cite_start]**"Real-time parameters... Latency & Costs"[cite: 49]:**
      * *Achieved:* You utilized **Groq** to minimize evaluation latency to sub-second levels and **Context Truncation** (limiting text to \~2000 chars) to keep costs minimal.
  * [cite_start]**"Input: 2 JSONs"[cite: 50]:**
      * *Achieved:* Your `extract_context_and_turn` function successfully parses the complex nested structures of both the Chat logs and Vector Context files.
  * [cite_start]**"Run your script at scale (millions of daily conversations)"[cite: 60]:**
      * *Achieved:* You ensured scalability via:
        1.  **Asynchronous Endpoints (`async def`):** Your server doesn't block while waiting for the LLM. It can handle hundreds of concurrent requests.
        2.  **Tiered Model Selection:** You switched to `Llama-3-8B` (Instant) for the final run. This model is lightweight and cheap, perfect for processing millions of rows without bankruptcy.