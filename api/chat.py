import asyncio
import fitz  # PyMuPDF
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Union

from services.llm_service import generate_response

router = APIRouter()

@router.post("/chat")
async def post_chat(
    session_id: str = Form(...),
    message: str = Form(...),
    # Allow the type to be a standard UploadFile OR a string fallback from Swagger/Frontends
    file: Optional[Union[UploadFile, str]] = File(None) 
):
    try:
        report_content = None
        
        # Check if a file was provided and ensure it's not just an empty form string
        if file and isinstance(file, UploadFile) and file.filename != "":
            if file.content_type == 'application/pdf':
                try:
                    pdf_bytes = await file.read()
                    
                    def extract_text():
                        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                        text = "".join([page.get_text() for page in doc])
                        doc.close()
                        return text

                    report_content = await asyncio.to_thread(extract_text)
                    print(f"Successfully extracted {len(report_content)} characters via background thread.")
                except Exception as e:
                    print(f"Error processing PDF file: {e}")
                    raise HTTPException(status_code=500, detail="Error processing PDF file.")
        
        # Pass data cleanly to the graph service
        ai_response = generate_response(session_id, message, report_content)
        
        return JSONResponse(content={"response": ai_response})

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))