<<<<<<< HEAD

import base64
import uuid
from pdf2image import convert_from_path
import pytesseract #type: ignore
import pdfplumber
from PIL import Image
from pdfminer.high_level import extract_text
import fitz #type: ignore
=======
>>>>>>> e0b1edd7f11f5617799aca94d4c113234e3f64fc
from fastapi import FastAPI, HTTPException, Query
from sqlmodel import SQLModel, Field, select
from fastapi.responses import JSONResponse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from Database.db import create_tables
from Database.setting import DB_SESSION, sendername, senderemail, SMTP_PASSWORD
<<<<<<< HEAD
from io import BytesIO
import base64
=======
import fitz #type: ignore
import pytesseract #type: ignore
from PIL import Image
import io
import base64

>>>>>>> e0b1edd7f11f5617799aca94d4c113234e3f64fc


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    pdf_sent: str | None = None  # Field to store the PDF file name sent to the user



# FastAPI app
app = FastAPI(lifespan = create_tables)

# Static PDF File Path (replace with your actual path)
<<<<<<< HEAD
PDF_PATH = Path(__file__).parent / "pdfs" / "MANAPRODUCTLIST.pdf"  # Path to the PDF

in_memory_images = {}

=======
PDF_PATH = Path(__file__).parent / "pdfs" / "MANAPRODUCTLIST.pdf"  # Use Path for PDF path
>>>>>>> e0b1edd7f11f5617799aca94d4c113234e3f64fc
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

        # Extract images from the page
        images = []
        image_list = page.get_images(full=True)
        if image_list:
            for img in image_list:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_extension = base_image["ext"]

                # Create an in-memory stream for the image
                image_io = BytesIO(image_bytes)

                # Generate a unique ID for the image
                image_id = str(uuid.uuid4())

                # Store the in-memory image with the ID
                in_memory_images[image_id] = {
                    "image_io": image_io,
                    "extension": image_extension
                }

                # Append the short path to the images list
                images.append(f"/get-image/{image_id}")

        # If no text and no images, notify the user
        if not text.strip() and not images:
            text = "[No extractable text or images found on this page]"

        # Prepare the response
        response = {
            "page_number": page_num,
            "total_pages": total_pages,
            "text": text if text.strip() else None,
            "images": images if images else None,
            "message": "Would you like to pr"
        }
        if page_num < total_pages:
            response["message"] = f"Page {page_num} of {total_pages}. Would you like to proceed to the next page?"
        else:
            response["message"] = f"Page {page_num} of {total_pages}. This is the last page."
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")

  

@app.get("/get-emails/")
def get_emails(session: DB_SESSION):
    return session.exec(select(User)).all()  # Retrieve all users


<<<<<<< HEAD
# @app.get("/read-pdf-step/", response_class=JSONResponse)
# async def read_pdf_step(page_num: int = Query(1, description="Page number to read")):
#     # Check if the PDF file exists
#     if not PDF_PATH.exists():
#         raise HTTPException(status_code=404, detail="PDF file not found.")

#     try:
#         # Convert the PDF page to an image
#         images = convert_from_path(PDF_PATH, first_page=page_num, last_page=page_num)
#         if not images:
#             raise HTTPException(status_code=400, detail="Page not found.")

#         # Perform OCR on the image
#         page_image = images[0]
#         text = pytesseract.image_to_string(page_image)

#         # If no text is found
#         if not text.strip():
#             text = "[No extractable text found on this page]"

#         # Return the extracted text
#         response = {
#             "page_number": page_num,
#             "text": text,
#             "message": "Text extracted using OCR."
#         }

#         return response

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")


=======
>>>>>>> e0b1edd7f11f5617799aca94d4c113234e3f64fc
# Route to read and return the PDF content
# @app.get("/read-pdf/", response_class=JSONResponse)
# async def read_pdf_with_ocr():
#     # Check if the PDF file exists
#     if not PDF_PATH.exists():
#         raise HTTPException(status_code=404, detail="PDF file not found.")
    
#     try:
#         # Open the PDF with PyMuPDF (fitz)
#         doc = fitz.open(str(PDF_PATH))
#         extracted_text = ""
#         images = []  # List to store base64 encoded images
        
#         # Iterate over PDF pages
#         for page_num in range(len(doc)):
#             page = doc.load_page(page_num)  # Load the page
#             pix = page.get_pixmap()  # Render the page as an image
            
#             # Convert the image to a base64 string
#             img_bytes = pix.tobytes("png")
#             base64_img = base64.b64encode(img_bytes).decode('utf-8')
#             images.append(base64_img)  # Append the base64 image to the list
            
#             # Convert the image to PIL format and extract text using pytesseract
#             img = Image.open(io.BytesIO(img_bytes))
#             text = pytesseract.image_to_string(img)
#             extracted_text += f"Page {page_num + 1}:\n{text}\n\n"
        
#         # If no text is found, we notify the user
#         if not extracted_text.strip():
#             extracted_text = "[No extractable text found in the PDF]"
        
#         # Return the extracted text and images
#         return {"pdf_content": extracted_text, "images": images}
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to read PDF with OCR: {e}")


# @app.get("/read-pdf-step/", response_class=JSONResponse)
# async def read_pdf_step(page_num: int = Query(1, description="Page number to read")):
#     # Check if the PDF file exists
#     if not PDF_PATH.exists():
#         raise HTTPException(status_code=404, detail="PDF file not found.")

#     try:
#         # Open the PDF file with PyMuPDF (fitz)
#         doc = fitz.open(str(PDF_PATH))
#         total_pages = len(doc)

#         # Check if the page number is valid
#         if page_num < 1 or page_num > total_pages:
#             raise HTTPException(status_code=400, detail=f"Invalid page number. The PDF has {total_pages} pages.")

#         # Load the specified page
#         page = doc.load_page(page_num - 1)  # Zero-indexed in PyMuPDF

#         # Extract text from the page
#         text = page.get_text("text").strip()

#         # If the default method doesn't work, try extracting blocks of text (list of blocks)
#         if not text:
#             blocks = page.get_text("blocks")
#             text = "\n".join([block[4] for block in blocks if block[4].strip()])

#         # If still no text, try extracting individual words (list of words)
#         if not text:
#             words = page.get_text("words")
#             text = " ".join([word[4] for word in words])

#         # If still no text, notify the user
#         if not text.strip():
#             text = "[No extractable text found on this page]"

#         # Extract images from the page
#         images = []
#         for img_index, img in enumerate(page.get_images(full=True)):
#             xref = img[0]  # Extract the xref of the image
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             image_base64 = base64.b64encode(image_bytes).decode('utf-8')  # Encode image to base64
#             images.append({
#                 "image_index": img_index, 
#                 "image_base64": image_base64
#             })

#         # Return the extracted text and images for the current page
#         response = {
#             "page_number": page_num,
#             "total_pages": total_pages,
#             "text": text,
#             "images": images
#         }

#         # Add a message prompting the user if they want to read the next page
#         response["message"] = f"Do you want to read the next page? The PDF has {total_pages} pages in total."

#         return response

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")


<<<<<<< HEAD
=======
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

        # If the default method doesn't work, try extracting blocks of text (list of blocks)
        if not text:
            blocks = page.get_text("blocks")
            text = "\n".join([block[4] for block in blocks if block[4].strip()])

        # If still no text, try extracting individual words (list of words)
        if not text:
            words = page.get_text("words")
            text = " ".join([word[4] for word in words])

        # If still no text, notify the user
        if not text.strip():
            text = "[No extractable text found on this page]"

        # Return the extracted text for the current page
        response = {
            "page_number": page_num,
            "total_pages": total_pages,
            "text": text
        }

        # Add a message prompting the user if they want to read the next page
        response["message"] = f"Do you want to read the next page? The PDF has {total_pages} pages in total."

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {e}")


>>>>>>> e0b1edd7f11f5617799aca94d4c113234e3f64fc
# @app.get("/read-pdf/", response_class=FileResponse)
# async def read_pdf():
#     if not PDF_PATH.exists():
#         raise HTTPException(status_code=404, detail="PDF file not found.")
#     return FileResponse(PDF_PATH, media_type='application/pdf', filename=PDF_PATH.name)