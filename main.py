from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api import chat
from api import webhooks
from services import llm_service
from dotenv import load_dotenv

load_dotenv()
# --- STARTUP AND SHUTDOWN LOGIC ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs on startup to initialize the RAG pipeline.
    """
    print("Application startup...")
    llm_service.setup_rag_pipeline()
    yield
    print("Application shutdown.")

# --- MAIN FASTAPI APP INITIALIZATION ---
# (Must happen BEFORE including routers)
app = FastAPI(lifespan=lifespan)

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# --- API ROUTERS ---
# Included cleanly exactly once after app is defined
app.include_router(chat.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")  # Exposes /api/webhooks/telegram and /api/webhooks/whatsapp

# --- ROOT ENDPOINT ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the FitPal AI Coach API"}