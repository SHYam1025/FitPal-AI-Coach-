# FitPal AI Coach Backend

This backend powers the FitPal AI Coach, providing stateful, multi-channel interactions through various webhook platforms (Telegram, WhatsApp). The system is designed to efficiently handle real-time medical and fitness queries.

## FastAPI Router Layout
The backend leverages a modular **FastAPI Router Layout**, creating streamlined and scalable webhook ingestion paths. Telegram and WhatsApp entry points asynchronously delegate heavy payloads (like image or document text extraction) to background tasks to prevent timeout blocks on the main thread.

## LangGraph State Management Logic
The core reasoning engine is built around a complex **LangGraph state management logic**. Each conversation turn passes through a deterministic routing graph:
1.  **Intent Classification**: Determines if the user is logging calories, asking general questions, or sending medical documents.
2.  **Specialized Worker Nodes**: Branches execution to distinct RAG chat handlers, calorie logging parsers, or medical diagnostic report analyzers depending on the classified state.
3.  **State Unification**: Consolidates the response and smoothly writes to memory.

## Redis Caching Coordination Engine
State synchronization relies on a high-performance **Redis caching coordination engine**. Because platforms like Telegram send documents and their accompanying text captions as separate sequential webhooks, Redis acts as an ephemeral staging area. It locks the transaction until both the document binary and the text query arrive, perfectly merging them before invoking the LangGraph pipeline. Furthermore, Redis is used as the persistent session history datastore for Langchain.

## Memory-Safe PyMuPDF File Streaming Handlers
Document extraction uses **memory-safe PyMuPDF file streaming handlers**. Rather than downloading PDFs to disk, the server captures byte-streams directly into RAM via HTTP, processes the text layout through PyMuPDF (`fitz`), and immediately releases the memory, preventing storage bloat or disk IO bottlenecks on the server.
