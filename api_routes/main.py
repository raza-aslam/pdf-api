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

@app.get("/read-pdf-step/", response_class=JSONResponse)
async def read_pdf_step(request: Request, page_num: int = Query(1, description="Page number to read")):
    # Check if the PDF file exists
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    try:
        # Open the PDF with PyMuPDF (Fitz) to determine the total number of pages
        doc = fitz.open(PDF_PATH)
        total_pages = len(doc)

        # Check if the requested page number is valid
        if page_num < 1 or page_num > total_pages:
            raise HTTPException(status_code=400, detail=f"Invalid page number. The PDF has {total_pages} pages.")

        # Prepare the response data
        response_data = {
            "page_number": page_num,
            "total_pages": total_pages
        }

        # Use a fixed image ID based on the page number
        image_id = f"page-{page_num}"

        # Check if the image is already in memory; if not, create and store it
        if image_id not in in_memory_images:
            # Render the page as an image using PyMuPDF
            page = doc.load_page(page_num - 1)  # Zero-indexed in PyMuPDF
            pix = page.get_pixmap()  # Render the page to an image
            img_io = BytesIO(pix.tobytes("png"))  # Convert image to bytes
            img_io.seek(0)

            # Store the image in memory with the fixed image_id
            in_memory_images[image_id] = {"image_io": img_io, "extension": "png"}

        # Generate the image URL for the response
        image_url: str = f"{request.base_url}get-image/{image_id}"
        response_data["image_url"] = image_url

        # Extract text from the page using PyMuPDF, but skip text extraction for page 3
        if page_num != 3:
            page = doc.load_page(page_num - 1)  # Zero-indexed in PyMuPDF
            text = page.get_text("text").strip()

            # Include text only if it's not empty
            if text:
                response_data["text"] = text

        return JSONResponse(content=response_data, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")


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