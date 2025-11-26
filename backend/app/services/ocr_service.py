from PIL import Image, ImageEnhance
from pdf2image import convert_from_path
import easyocr
from typing import Tuple
import io
import numpy as np
import cv2
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (lazy loading)
_easyocr_reader = None


def get_easyocr_reader():
    """Lazy load EasyOCR reader"""
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


def score_extracted_text(text: str) -> float:
    """
    Heuristic quality score for OCR output.
    Combines length, digit coverage, and number of unique words.
    """
    if not text:
        return 0.0
    stripped = text.strip()
    if not stripped:
        return 0.0
    words = stripped.split()
    unique_words = len(set(w.lower() for w in words if len(w) > 2))
    digits = sum(ch.isdigit() for ch in stripped)
    lines = [line for line in stripped.splitlines() if line.strip()]
    score = len(words) + digits * 0.4 + unique_words * 0.6 + len(lines) * 0.3
    return score


def run_easyocr(image: Image.Image) -> Tuple[str, float]:
    """Run EasyOCR and return text with score."""
    reader = get_easyocr_reader()
    img_array = np.array(image)
    result = reader.readtext(img_array, detail=0, paragraph=False)
    if isinstance(result, list):
        text = "\n".join(result)
    else:
        text = str(result or "")
    return text.strip(), score_extracted_text(text)


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy with deskewing for angled receipts
    
    Args:
        image: PIL Image
    
    Returns:
        Preprocessed PIL Image
    """
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to numpy array for OpenCV processing
    img_array = np.array(image)
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    # Apply adaptive thresholding for better contrast
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Deskewing for angled receipts
    # Find coordinates of all non-zero pixels
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 100:  # Only if we have enough points
        # Find minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Correct angle based on quadrant
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        
        # Only rotate if there's significant skew (more than 0.5 degrees)
        if abs(angle) > 0.5:
            h, w = thresh.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, M, (w, h), 
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            logger.debug(f"Deskewed image by {angle:.2f} degrees")
    
    # Convert back to PIL Image
    processed_image = Image.fromarray(thresh)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(processed_image)
    processed_image = enhancer.enhance(1.5)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(processed_image)
    processed_image = enhancer.enhance(1.5)
    
    return processed_image


async def extract_text_from_image(
    image_bytes: bytes,
    ocr_engine: str = None
) -> str:
    """
    Extract text from image using EasyOCR with multi-strategy preprocessing
    
    Args:
        image_bytes: Image file bytes
        ocr_engine: Not used, kept for API compatibility
    
    Returns:
        Extracted text string
    """
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Strategy 1: Original image
        text_original, score_original = run_easyocr(image)
        logger.info(f"Original image OCR (score={score_original:.2f}, length={len(text_original)})")
        
        # Strategy 2: Preprocessed image
        preprocessed_image = preprocess_image_for_ocr(image)
        text_preprocessed, score_preprocessed = run_easyocr(preprocessed_image)
        logger.info(f"Preprocessed image OCR (score={score_preprocessed:.2f}, length={len(text_preprocessed)})")
        
        # Choose the best result based on score
        if score_preprocessed > score_original:
            logger.info(f"Using preprocessed result (score={score_preprocessed:.2f})")
            return text_preprocessed.strip()
        else:
            logger.info(f"Using original result (score={score_original:.2f})")
            return text_original.strip()
    
    except Exception as e:
        logger.error(f"OCR extraction error: {e}", exc_info=True)
        raise Exception(f"Failed to extract text from image: {str(e)}")


async def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF file
    
    Args:
        pdf_bytes: PDF file bytes
    
    Returns:
        Extracted text string
    """
    try:
        # Save PDF to temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Convert PDF to images
            images = convert_from_path(tmp_path, dpi=300)
            text_parts = []
            
            for i, image in enumerate(images):
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                page_text = await extract_text_from_image(buffer.getvalue())
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            return "\n\n".join(text_parts).strip()
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

