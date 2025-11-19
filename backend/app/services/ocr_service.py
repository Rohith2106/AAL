import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pdf2image import convert_from_path
import easyocr
from typing import Union, List, Tuple
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


def deskew_image(image: Image.Image) -> Image.Image:
    """Deskew image to improve OCR accuracy."""
    img_array = np.array(image.convert("L"))
    coords = np.column_stack(np.where(img_array > 0))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img_array.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img_array, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(rotated).convert("RGB")


def generate_tesseract_variants(image: Image.Image) -> List[Image.Image]:
    """
    Generate multiple pre-processed variants for Tesseract to improve accuracy.
    """
    variants = []
    base = preprocess_image_for_ocr(image)
    variants.append(base)

    # Slightly increased contrast
    enhancer = ImageEnhance.Contrast(base)
    variants.append(enhancer.enhance(1.8))

    # Median filter to reduce salt-and-pepper noise
    variants.append(base.filter(ImageFilter.MedianFilter(size=3)))

    # Inverted image for receipts with dark background
    variants.append(ImageOps.invert(base))

    # Deskewed variant
    try:
        variants.append(preprocess_image_for_ocr(deskew_image(image)))
    except Exception:
        pass

    # Ensure uniqueness while preserving order
    unique_variants = []
    seen_ids = set()
    for variant in variants:
        variant_id = variant.tobytes()
        if variant_id not in seen_ids:
            unique_variants.append(variant)
            seen_ids.add(variant_id)
    return unique_variants or [base]


def run_tesseract(image: Image.Image, lang: str = "eng") -> Tuple[str, float]:
    """Run Tesseract across multiple variants and return best text with score."""
    best_text = ""
    best_score = 0.0
    custom_config = (
        r'--oem 3 --psm 6 '
        r'-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,$/-:'
    )

    for variant in generate_tesseract_variants(image):
        text = pytesseract.image_to_string(variant, lang=lang, config=custom_config)
        score = score_extracted_text(text)
        if score > best_score:
            best_score = score
            best_text = text

    # As a final fallback, run on original image if everything failed
    if best_score < 15:
        fallback_text = pytesseract.image_to_string(image, lang=lang, config=custom_config)
        fallback_score = score_extracted_text(fallback_text)
        if fallback_score > best_score:
            best_text, best_score = fallback_text, fallback_score

    return best_text.strip(), best_score


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
    Preprocess image to improve OCR accuracy
    
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
    
    # Convert back to PIL Image
    processed_image = Image.fromarray(thresh)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(processed_image)
    processed_image = enhancer.enhance(1.5)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(processed_image)
    processed_image = enhancer.enhance(2.0)
    
    return processed_image


async def extract_text_from_image(
    image_bytes: bytes,
    ocr_engine: str = None
) -> str:
    """
    Extract text from image using OCR with preprocessing
    
    Args:
        image_bytes: Image file bytes
        ocr_engine: 'tesseract' or 'easyocr'
    
    Returns:
        Extracted text string
    """
    engine = (ocr_engine or settings.OCR_ENGINE or "tesseract").lower()
    
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        candidates: List[Tuple[str, float, str]] = []

        if engine in ("tesseract", "auto"):
            text, score = run_tesseract(image)
            candidates.append((text, score, "tesseract"))

        if engine in ("easyocr", "auto"):
            text, score = run_easyocr(image)
            candidates.append((text, score, "easyocr"))

        # If a specific engine was requested but produced very low quality text,
        # automatically fall back to the other engine.
        if not candidates or max(c[1] for c in candidates) < 10:
            alt_engine = "easyocr" if engine == "tesseract" else "tesseract"
            logger.info(f"OCR quality low with {engine}, trying fallback engine: {alt_engine}")
            if alt_engine == "tesseract":
                candidates.append((*run_tesseract(image), "tesseract"))
            else:
                candidates.append((*run_easyocr(image), "easyocr"))

        # Select best candidate
        best_text, best_score, best_engine = max(candidates, key=lambda x: x[1])
        logger.info(f"OCR selected engine: {best_engine} (score={best_score:.2f}, length={len(best_text)})")

        return best_text.strip()
    
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
                page_text = await extract_text_from_image(
                    buffer.getvalue(),
                    ocr_engine=settings.OCR_ENGINE
                )
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            return "\n\n".join(text_parts).strip()
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

