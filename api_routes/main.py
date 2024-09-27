from PyPDF2 import PdfReader
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, select
from fastapi.responses import JSONResponse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from Database.db import create_tables
from Database.setting import DB_SESSION, sendername, senderemail, SMTP_PASSWORD
import base64
from io import BytesIO
from PIL import Image
import pdfplumber

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    pdf_sent: str | None = None  # Field to store the PDF file name sent to the user



# FastAPI app
app = FastAPI(lifespan = create_tables)

# Static PDF File Path (replace with your actual path)
PDF_PATH = Path(__file__).parent / "pdfs" / "book.pdf"  # Use Path for PDF path
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

@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users



def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

@app.get("/read-pdf/")
async def read_pdf():
    # Check if the PDF file exists
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    pdf_content = {"text": "", "images": []}

    try:
        # Use pdfplumber to read the PDF content
        with pdfplumber.open(PDF_PATH) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                # Extract text
                pdf_content["text"] += f"Page {page_number}:\n"
                pdf_content["text"] += page.extract_text() or "No text found\n"

                # Extract images
                for img in page.images:
                    # Coordinates of the image in the PDF
                    x0, y0, x1, y1 = img["x0"], img["y0"], img["x1"], img["y1"]
                    # Cropping image from the PDF
                    cropped_image = page.within_bbox((x0, y0, x1, y1)).to_image()
                    pil_image = cropped_image.original  # PIL image object
                    base64_image = image_to_base64(pil_image)  # Convert to base64
                    pdf_content["images"].append({
                        "page_number": page_number,
                        "image_data": base64_image
                    })

        return JSONResponse(content={"pdf_content": pdf_content}, status_code=200)
    except Exception as e:
        print(f"Failed to read PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to read PDF content")