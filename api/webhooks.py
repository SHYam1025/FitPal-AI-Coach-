import os
import httpx
import fitz  # PyMuPDF
import redis
import traceback
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from services.llm_service import generate_response

router = APIRouter()

# Initialize standard Redis connection mapping to your current environment setup
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def extract_text_from_telegram_pdf(file_id: str) -> str:
    """
    Hits the Telegram Bot API to fetch the file path, downloads the raw 
    PDF binary stream into memory, and extracts its plaintext layout.
    """
    try:
        async with httpx.AsyncClient() as client:
            get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
            file_info_res = await client.get(get_file_url, params={"file_id": file_id}, timeout=10.0)
            
            if file_info_res.status_code != 200:
                print(f"⚠️ Failed to call getFile API from Telegram: {file_info_res.text}")
                return ""
                
            file_path = file_info_res.json().get("result", {}).get("file_path")
            if not file_path:
                print("⚠️ Telegram getFile response did not contain a valid file_path.")
                return ""
                
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            print(f"📡 Downloading file stream from: https://api.telegram.org/file/bot.../{file_path}")
            file_content_res = await client.get(download_url, timeout=20.0)
            
            if file_content_res.status_code != 200:
                print("⚠️ Failed to download the target binary asset file content.")
                return ""
                
            pdf_bytes = file_content_res.content
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text()
                
            doc.close()
            print(f"✅ Extracted {len(extracted_text)} characters from health report document.")
            return extracted_text.strip()
            
    except Exception as e:
        print(f"❌ Failed during async file parsing routine: {e}")
        traceback.print_exc()
        return ""

async def process_telegram_message(payload: dict):
    """
    Worker function that handles asynchronous file processing and message cross-referencing
    using a shared Redis staging cache layer.
    """
    try:
        if "message" not in payload:
            return
            
        message_data = payload["message"]
        chat_id = str(message_data["chat"]["id"])
        
        # Build Redis cache keys unique to this incoming transaction turn
        pdf_cache_key = f"tmp_pdf_cache:{chat_id}"
        msg_cache_key = f"tmp_msg_cache:{chat_id}"
        
        user_text = message_data.get("text") or message_data.get("caption") or ""
        
        # --- CASE 1: Webhook contains the PDF document binary metadata ---
        if "document" in message_data:
            file_id = message_data["document"]["file_id"]
            file_name = message_data["document"].get("file_name", "")
                
            if file_name.lower().endswith(".pdf"):
                print(f"📥 Telegram document payload detected with file_id: {file_id}")
                report_content = await extract_text_from_telegram_pdf(file_id)
                
                if report_content:
                    # Cache the text for 60 seconds to wait for the matching text query turn
                    redis_client.set(pdf_cache_key, report_content, ex=60)
                    print(f"💾 Staged extracted PDF text in Redis cache for Session: {chat_id}")

        # --- CASE 2: Webhook contains the standalone text query question ---
        if user_text:
            # Cache the user prompt text for 60 seconds to wait for the heavy PDF extraction loop turn
            redis_client.set(msg_cache_key, user_text, ex=60)
            print(f"💾 Staged user text query prompt in Redis cache for Session: {chat_id}")

        # --- RECONCILIATION TURN CONTROL ---
        # Fetch both items from the temporary Redis staging bucket
        cached_pdf = redis_client.get(pdf_cache_key)
        cached_msg = redis_client.get(msg_cache_key)
        
        # If one of the pieces is still processing, exit this turn task early.
        # The secondary asynchronous webhook turn task will trigger the execution loop.
        if not cached_pdf or not cached_msg:
            print("⏳ Holding transaction: Waiting for companion webhook event to finish sync...")
            return

        print(f"🚀 Perfect Sync! Executing LangGraph for session telegram_{chat_id}...")
        print(f"📥 [Telegram Query] Msg: '{cached_msg}'")
        
        # Remove temporary cache states so subsequent interactions start clean
        redis_client.delete(pdf_cache_key)
        redis_client.delete(msg_cache_key)

        # Invoke core execution pipelines with both verified state elements
        ai_reply = generate_response(session_id=f"telegram_{chat_id}", message=cached_msg, report_content=cached_pdf)
        
        # Dispatch the multi-chunk outbound message responses
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        MAX_LENGTH = 4000
        message_chunks = [ai_reply[i:i+MAX_LENGTH] for i in range(0, len(ai_reply), MAX_LENGTH)]
        
        async with httpx.AsyncClient() as client:
            for chunk in message_chunks:
                await client.post(
                    telegram_url, 
                    json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"},
                    timeout=15.0
                )
        print(f"🏁 [Telegram Success] Full response distributed cleanly without overflow.")
            
    except Exception as e:
        print(f"❌ CRITICAL WEBHOOK CRASH:")
        traceback.print_exc()

async def process_whatsapp_message(payload: dict):
    try:
        from_number = payload.get("From", "")
        incoming_body = payload.get("Body", "")
        if from_number:
            ai_reply = generate_response(session_id=f"whatsapp_{from_number}", message=incoming_body)
            print(f"Dispatched WhatsApp reply out to provider for channel session {from_number}")
    except Exception as e:
        print(f"Failed to process background whatsapp message task: {e}")


# --- WEBHOOK ENTRYPOINT ROUTES ---

@router.post("/webhooks/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_telegram_message, payload)
    return {"status": "queued"}


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    payload = dict(form_data)
    background_tasks.add_task(process_whatsapp_message, payload)
    return {"status": "queued"}