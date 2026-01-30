import pytesseract
from PIL import Image
import io
import logging
import fitz # PyMuPDF

# Set up logging
logger = logging.getLogger(__name__)

# NOTE: If tesseract is not in your PATH, you might need to specify the path:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Convert image to grayscale and apply thresholding.
    """
    # Convert to grayscale
    logger.info(f"Preprocessing image. Size: {image.size}, Mode: {image.mode}")
    gray = image.convert('L')
    
    # Apply binary thresholding
    # Pixels > 128 become 255 (white), others become 0 (black)
    threshold = 128
    processed = gray.point(lambda p: 255 if p > threshold else 0)
    
    return processed

def extract_text_from_image_bytes(file_bytes: bytes) -> str:
    """
    Helper to extract text from a single image file bytes.
    """
    image = Image.open(io.BytesIO(file_bytes))
    processed_image = preprocess_image(image)
    return pytesseract.image_to_string(processed_image)

def extract_text(file_bytes: bytes) -> str:
    """
    Takes raw file bytes (image or PDF), preprocesses, and extracts text using Tesseract.
    """
    try:
        # Check if it's a PDF signature
        if file_bytes.startswith(b'%PDF'):
            logger.info("Detected PDF file. Rendering pages to images...")
            text_pages = []
            
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                logger.info(f"PDF has {len(doc)} pages.")
                for page_num, page in enumerate(doc):
                    # Render page to image (pixmap)
                    # Zoom = 2 to improve resolution for OCR
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    logger.info(f"Processing PDF page {page_num + 1}/{len(doc)}")
                    # Preprocess
                    processed = preprocess_image(img)
                    
                    # OCR
                    page_text = pytesseract.image_to_string(processed)
                    text_pages.append(page_text)
            
            return "\n\n".join(text_pages).strip()

        else:
            # Assume Image
            return extract_text_from_image_bytes(file_bytes)

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise e
