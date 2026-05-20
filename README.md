# FitPal AI Coach Backend 🚀

![FitPal AI Coach — System Architecture Banner](assets/banner.png)

This production-grade backend engine powers the FitPal AI Coach ecosystem, distributing stateful, multi-channel fitness, nutrition, and medical report analytics across interactive webhook layers (<code>Telegram</code> and <code>WhatsApp Business</code>).

---

## 🛠️ Unified System Technology Stack

| Architecture Component | Technology Stack | Core Processing Responsibility |
| :--- | :--- | :--- |
| <code>API Webhook Gateway</code> | <code>FastAPI</code> / <code>Uvicorn</code> | High-throughput, non-blocking asynchronous payload ingestion paths. |
| <code>Stateful Graph Router</code> | <code>LangGraph</code> / <code>LangChain</code> | Deterministic multi-node intent routing, state unification, and execution flows. |
| <code>Session Cache Store</code> | <code>Redis DB</code> (Port <code>6379</code>) | Ephemeral request synchronization and persistent multi-turn message history storage. |
| <code>Document Extraction</code> | <code>PyMuPDF</code> (<code>Fitz Engine</code>) | Low-overhead, memory-safe direct binary RAM byte-stream PDF processing. |
| <code>Intelligence Model</code> | Native <code>Google Gemini API</code> | Advanced context extraction, intent classification, and responsive coaching. |

---

## 📂 Project Directory Structure

```text
fitness_ai_app/
├── api/
│   ├── __init__.py
│   └── webhooks.py          # Dual-channel Telegram & Twilio webhook ingestors
├── services/
│   ├── __init__.py
│   └── llm_service.py       # Core LangGraph pipeline & intent routing logic
├── vectors/                 # Local vector storage knowledge bases
├── .env                     # Secure deployment credentials (ignored by git)
├── .gitignore               # Strict DevSecOps tracking exclusion layout
├── main.py                  # Primary FastAPI lifecycle initializer entrypoint
├── requirements.txt         # Consolidated production dependency manifest
├── sync_webhook.py          # Automated remote gateway sync registration utility
└── README.md                # System documentation landing page
```

---

## ⚙️ Core Architectural Pillars

### 📡 FastAPI Asynchronous Router Layout

The backend leverages a modular router blueprint designed to handle high-concurrency mobile streaming webhooks. Inbound data requests from messaging platforms are parsed instantly; any long-running transactions (such as downloading <code>2MB+</code> lab reports or running image vision extractions) are immediately offloaded to background threads. This ensures the main server loops return an instant <code>200 OK</code> connection handshake back to the external platform gateways, mitigating packet drops or duplicate retry triggers.

![Webhook Gateway Flow — Inbound Bot Ping Visualization](assets/screenshot_webhook_flow.png)

---

### 🔮 LangGraph Deterministic State Management

The system's reasoning center is structured around a <code>StateGraph</code> execution pipeline. Each conversational transaction undergoes a multi-node evaluation lifecycle:
- <code>Intent Classification Node</code>: Leverages structured output configurations to accurately isolate whether a user intends to log nutritional calories, seek general training advice, or request clinical laboratory record tracking.
- <code>Specialized Worker Nodes</code>: Branches routing dynamically based on state classification variables into isolated context processors (RAG chat nodes, macro-estimation parsers, or medical analysis engines).
- <code>State Unification Layer</code>: Normalizes language outputs under strict layout styling rules and commits the unified state history directly to <code>Redis</code> storage before exiting the turn.

![LangGraph Router Visualization — Bot Intent Routing Reply](assets/screenshot_langgraph_router.png)

---

### 💾 Redis Ephemeral Caching Coordination Engine

State synchronization relies on a high-performance <code>Redis</code> memory cache layer. Messaging applications like <code>Telegram</code> distribute media file uploads and their accompanying text captions as separate, non-simultaneous webhook events. To counteract this data fragmentation, <code>Redis</code> acts as a stateful staging area. It caches whichever event segment arrives first for up to <code>60 seconds</code>. The moment both elements are successfully captured, the background threads merge the prompt strings and the file data arrays perfectly before invoking the underlying <code>LangGraph</code> engine. <code>Redis</code> also manages persistent user chat history tracking across distinct <code>session_id</code> keys.

![Redis Handshake App Logs — Multi-turn Mobile Chat Session](assets/screenshot_redis_logs.png)

---

### 🧠 Memory-Safe PyMuPDF Data Streaming

Document processing uses a diskless, RAM-first extraction pipeline. Rather than dumping user health files to the server's local hard drive, the system streams raw document binaries straight into memory arrays via <code>HTTP</code>. The <code>PyMuPDF</code> (<code>fitz</code>) engine parses the text layers instantly from memory and passes the string chunks directly into the model context window. The temporary memory arrays are then flushed immediately, entirely bypassing local storage I/O limits, removing file deletion clean-up maintenance tasks, and securing sensitive user health data.

![Medical Report Processing — Mobile Screen Response View](assets/screenshot_pdf_analysis.png)

---

## 🔐 Security & DevSecOps Layout

The deployment surface is hardened at every layer. The <code>.env</code> file holds all runtime secrets (<code>GEMINI_API_KEY</code>, <code>TELEGRAM_BOT_TOKEN</code>, <code>REDIS_URL</code>) and is strictly excluded from <code>git</code> tracking via <code>.gitignore</code>. No raw API key strings are hardcoded inside any source files. All model provider credentials are loaded exclusively at runtime via <code>python-dotenv</code> and validated at startup, halting the server with a <code>ValueError</code> if any critical key is absent.

---

## ⚡ Local Development Setup

```bash
# Clone the repository
git clone https://github.com/SHYam1025/FitPal-AI-Coach-
cd fitness_ai_app

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all production dependencies
pip install -r requirements.txt

# Configure your environment credentials
cp .env.example .env
# Edit .env and populate: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, REDIS_URL

# Start the local Redis daemon (Homebrew)
brew services start redis

# Launch the FastAPI development server
uvicorn main:app --reload

# Register the active webhook tunnel endpoint
python sync_webhook.py
```

---

## 📦 Production Dependency Manifest

| Package | Role |
| :--- | :--- |
| <code>fastapi</code> | Async web framework and router engine |
| <code>uvicorn[standard]</code> | ASGI server for production-grade concurrency |
| <code>python-dotenv</code> | Secure runtime environment variable loader |
| <code>langchain</code> / <code>langchain-core</code> | Base chain orchestration and prompt management |
| <code>langchain-google-genai</code> | Native <code>Google Gemini</code> model provider adapter |
| <code>langgraph</code> | Stateful multi-node graph execution engine |
| <code>PyMuPDF</code> | Memory-safe PDF binary stream parser |
| <code>redis</code> | Ephemeral cache client and session history store |
| <code>faiss-cpu</code> | High-speed local vector similarity search index |

---

## 📬 Webhook Channel Architecture

| Channel | Inbound Route | Processing Method |
| :--- | :--- | :--- |
| <code>Telegram Bot</code> | <code>POST /webhooks/telegram</code> | Async background task with Redis staging sync |
| <code>WhatsApp (Twilio)</code> | <code>POST /webhooks/whatsapp</code> | Async background task with direct LangGraph dispatch |

---

*Built with precision for real-world production fitness coaching deployments.*
