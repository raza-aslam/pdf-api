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
@app.get("/read-pdf-steps/", response_class=JSONResponse)
async def read_pdf_steps(request: Request, keyword: str):
    # Check karein ke PDF file mojood hai ya nahi
    if not PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF file nahi mili.")

    try:
        # PDF ko open karein using PyMuPDF (Fitz)
        doc = fitz.open(PDF_PATH)
        total_pages = len(doc)
        response_data = {"total_pages": total_pages}
        matches = []

        # Har page par keyword ko search karein
        for page_num in range(total_pages):
            page = doc.load_page(page_num)  # Page ko load karen
            text = page.get_text("text")
            
            if keyword.lower() in text.lower():  # Case-insensitive search
                # Agar keyword match kare to usko list mein add karen
                matches.append({
                    "page_number": page_num + 1,  # Page number ko 1-based index mein rakhein
                    "text_snippet": text.strip()[:200]  # Text ka snippet dikhayein
                })

                # Image ko generate karein aur memory mein store karen
                image_id = f"page-{page_num + 1}"
                if image_id not in in_memory_images:
                    pix = page.get_pixmap()  # Page ko image mein render karen
                    img_io = BytesIO(pix.tobytes("png"))  # Image ko bytes mein convert karen
                    img_io.seek(0)
                    in_memory_images[image_id] = {"image_io": img_io, "extension": "png"}

                # Add image URL for the match
                matches[-1]["image_url"] = f"{request.base_url}get-image/{image_id}"

        if not matches:
            return JSONResponse(content={"message": f"Keyword '{keyword}' ke liye koi matches nahi mile."}, status_code=404)

        response_data["matches"] = matches
        response_data["total_matches"] = len(matches)
        return JSONResponse(content=response_data, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF ko search karne mein error: {e}")



# Endpoint to retrieve images by their unique ID
# # Image ko unique ID ke zariye retrieve karne ka endpoint
@app.get("/get-image/{image_id}")
async def get_image(image_id: str):
    image_info = in_memory_images.get(image_id)
    if image_info:
        image_io = image_info["image_io"]
        image_extension = image_info["extension"]
        # Stream ko shuru se set karen
        image_io.seek(0)
        return StreamingResponse(image_io, media_type=f"image/{image_extension}")
    else:
        raise HTTPException(status_code=404, detail="Image not found.")


@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users