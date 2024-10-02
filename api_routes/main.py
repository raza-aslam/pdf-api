

import base64
from io import BytesIO
import uuid
from pdf2image import convert_from_path
import pytesseract #type: ignore
import pdfplumber
from PIL import Image
from pdfminer.high_level import extract_text
import fitz #type: ignore

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import SQLModel, Field, select
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from Database.db import create_tables
from Database.setting import DB_SESSION, sendername, senderemail, SMTP_PASSWORD



class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    pdf_sent: str | None = None  # Field to store the PDF file name sent to the user



# FastAPI app
app = FastAPI(lifespan = create_tables)


PDF_PATH = Path(__file__).parent / "pdfs" / "MANAPRODUCTLIST.pdf"  # Path to the PDF
IMAGE_DIR = Path(__file__).parent / "temp_images"
IMAGE_DIR.mkdir(exist_ok=True)  # Create the directory if it doesn't exist
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

@app.get("/read-pdf-step/", response_class=JSONResponse)
async def read_pdf_step(page_num: int = Query(1, description="Page number to read")):
    try:
        # Open the PDF file
        doc = fitz.open(PDF_PATH)
        total_pages = len(doc)

        if page_num < 1 or page_num > total_pages:
            raise HTTPException(status_code=400, detail=f"Invalid page number. The PDF has {total_pages} pages.")

        page = doc.load_page(page_num - 1)
        
        # Extract text from the page
        text = page.get_text("text").strip()

        # Extract images from the page
        image_urls = []
        image_list = page.get_images(full=True)
        
        if image_list:
            for img_index, img in enumerate(image_list):
                # Generate a URL to fetch each image
                image_url = f"/image/{page_num}/{img_index}"
                image_urls.append(image_url)

        # Prepare the response
        response = {
            "page_number": page_num,
            "total_pages": total_pages,
            "text": text if text else "[No text found on this page]",
            "images": image_urls
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {str(e)}")


@app.get("/image/{page_num}/{img_index}")
async def get_image(page_num: int, img_index: int):
    try:
        # Open the PDF file
        doc = fitz.open(PDF_PATH)
        page = doc.load_page(page_num - 1)

        # Extract the image based on the index
        image_list = page.get_images(full=True)
        
        if img_index < 0 or img_index >= len(image_list):
            raise HTTPException(status_code=404, detail="Image not found")

        img = image_list[img_index]
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]

        # Use Pillow to handle the image in-memory
        image = Image.open(BytesIO(image_bytes))
        img_io = BytesIO()
        image.save(img_io, format="PNG")
        img_io.seek(0)

        # Serve the image directly as a response
        return StreamingResponse(img_io, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load image: {str(e)}")

@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users