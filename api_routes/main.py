from io import BytesIO
import os
import uuid
import fitz #type: ignore
from fastapi import FastAPI, HTTPException, Query, Request
from sqlmodel import SQLModel, Field, select
from fastapi.responses import JSONResponse, StreamingResponse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from Database.db import create_tables
from Database.setting import DB_SESSION, sendername, senderemail, SMTP_PASSWORD
from fastapi.middleware.cors import CORSMiddleware


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    pdf_sent: str | None = None  # Field to store the PDF file name sent to the user



# FastAPI app
app = FastAPI(lifespan = create_tables)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pdf-api-production-2f82.up.railway.app/"],  # Adjust this to your frontend's domain for better security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_PATH = Path(__file__).parent / "pdfs" / "MANAPRODUCTLIST.pdf"  # Path to the PDF

in_memory_images = {}


 # Ensure this is correct

# Static sender information
 # Static sender email

# Utility function to send email
def send_email_with_pdf(to_email: str, username: str):
    try:
        # Check if the PDF file exists
        if not PDF_PATH.exists():
            raise HTTPException(status_code=404, detail="PDF file not found.")
        
        pdf_file_name = PDF_PATH.name # Get the file name using pathlib
        
        # Email setup
        msg = EmailMessage()
        msg['Subject'] = f'Your PDF file {pdf_file_name}'
        msg['From'] = formataddr((sendername, senderemail))
        msg['To'] = to_email

        # Email body content
        msg.set_content(f"Hello {username},\n\nPlease find the requested PDF attached.")

        # Attach the PDF file
        with open(PDF_PATH, 'rb') as f:
            pdf_data = f.read()
        msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_file_name)

        # SMTP server connection
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(senderemail, SMTP_PASSWORD)  # Use the correct password or App Password
            smtp.send_message(msg)

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")  # Log the error
        raise HTTPException(status_code=500, detail=str(e))
    
    
    

@app.post("/send-pdf/")
async def send_pdf(username: str, email: str, session: DB_SESSION):
    # Add the users in the database with pdf files
    result = User(username=username, email=email, pdf_sent=PDF_PATH.name)
    session.add(result)
    session.commit()
    session.refresh(result)
        
    # Send the email
    email_sent = send_email_with_pdf(email, username)
    if email_sent:
        return JSONResponse(content={"message": f"PDF file sent successfully to {email}"}, status_code=200)
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")
@app.get("/search-pdf-keyword/", response_class=JSONResponse)
async def search_pdf_keyword(keyword: str):
    # Check if the PDF file exists
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")
    
    try:
        # Open the PDF with PyMuPDF (Fitz)
        doc = fitz.open(PDF_PATH)
        total_pages = len(doc)
        matches = []

        # Iterate through all the pages and search for the keyword
        for page_num in range(total_pages):
            page = doc.load_page(page_num)  # Load the page
            text = page.get_text("text")
            
            if keyword.lower() in text.lower():  # Case-insensitive search
                matches.append({
                    "page_number": page_num + 1,  # Store 1-based index for page numbers
                    "text_snippet": text.strip()[:200]  # Provide a snippet of the text
                })

        if not matches:
            return JSONResponse(content={"message": f"No matches found for keyword '{keyword}'"}, status_code=404)
        
        return JSONResponse(content={"matches": matches, "total_matches": len(matches)}, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search PDF: {e}")

# Endpoint to retrieve images by their unique ID
@app.get("/get-image/{image_id}")
async def get_image(image_id: str):
    image_info = in_memory_images.get(image_id)
    if image_info:
        image_io = image_info["image_io"]
        image_extension = image_info["extension"]
        # Reset the stream position to the beginning
        image_io.seek(0)
        return StreamingResponse(image_io, media_type=f"image/{image_extension}")
    else:
        raise HTTPException(status_code=404, detail="Image not found.")

@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users