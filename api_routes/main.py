from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, select
from fastapi.responses import JSONResponse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from Database.db import create_tables
from Database.setting import DB_SESSION, sendername, senderemail, SMTP_PASSWORD
import fitz #type: ignore
import pytesseract #type: ignore
from PIL import Image
import io
import base64



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


# Route to read and return the PDF content
@app.get("/read-pdf/", response_class=JSONResponse)
async def read_pdf_with_ocr():
    # Check if the PDF file exists
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")
    
    try:
        # Open the PDF with PyMuPDF (fitz)
        doc = fitz.open(str(PDF_PATH))
        extracted_text = ""
        images = []  # List to store base64 encoded images
        
        # Iterate over PDF pages
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)  # Load the page
            pix = page.get_pixmap()  # Render the page as an image
            
            # Convert the image to a base64 string
            img_bytes = pix.tobytes("png")
            base64_img = base64.b64encode(img_bytes).decode('utf-8')
            images.append(base64_img)  # Append the base64 image to the list
            
            # Convert the image to PIL format and extract text using pytesseract
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img)
            extracted_text += f"Page {page_num + 1}:\n{text}\n\n"
        
        # If no text is found, we notify the user
        if not extracted_text.strip():
            extracted_text = "[No extractable text found in the PDF]"
        
        # Return the extracted text and images
        return {"pdf_content": extracted_text, "images": images}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF with OCR: {e}")


# @app.get("/read-pdf/", response_class=FileResponse)
# async def read_pdf():
#     if not PDF_PATH.exists():
#         raise HTTPException(status_code=404, detail="PDF file not found.")
#     return FileResponse(PDF_PATH, media_type='application/pdf', filename=PDF_PATH.name)