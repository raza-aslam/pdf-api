

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
from fastapi.responses import FileResponse, JSONResponse
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
    # Check if the PDF file exists
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    try:
        # Open the PDF file with PyMuPDF (fitz)
        doc = fitz.open(str(PDF_PATH))
        total_pages = len(doc)

        # Check if the page number is valid
        if page_num < 1 or page_num > total_pages:
            raise HTTPException(status_code=400, detail=f"Invalid page number. The PDF has {total_pages} pages.")

        # Load the specified page
        page = doc.load_page(page_num - 1)  # Zero-indexed in PyMuPDF

        # Extract text from the page
        text = page.get_text("text").strip()

        # Extract images from the page and save them temporarily as files
        images = []
        image_list = page.get_images(full=True)
        if image_list:
            for img in image_list:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_extension = base_image["ext"]

                # Generate a unique filename for the image
                image_filename = f"{uuid.uuid4()}.{image_extension}"
                image_path = IMAGE_DIR / image_filename

                # Save the image to disk using Pillow
                try:
                    image = Image.open(BytesIO(image_bytes))
                    image.save(image_path)
                    # Append the short URL for the image
                    images.append(f"/get-image/{image_filename}")
                except Exception as e:
                    print(f"Failed to process image: {e}")
                    continue

        # If no text and no images, notify the user
        if not text.strip() and not images:
            text = "[No extractable text or images found on this page]"

        # Prepare the response
        response = {
            "page_number": page_num,
            "total_pages": total_pages,
            "text": text if text.strip() else None,
            "images": images if images else None
        }

        # Add a prompt message for proceeding to the next page
        if page_num < total_pages:
            response["message"] = f"Page {page_num} of {total_pages}. Would you like to proceed to the next page?"
        else:
            response["message"] = f"Page {page_num} of {total_pages}. This is the last page."

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")


@app.get("/get-image/{image_filename}")
async def get_image(image_filename: str):
    # Generate the full image path
    image_path = IMAGE_DIR / image_filename

    # Check if the image exists
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")

    # Return the image as a file response
    return FileResponse(image_path)

@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users