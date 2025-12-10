from PIL import Image, ImageEnhance
from pdf2image import convert_from_path
import easyocr
from typing import Tuple, Dict, Any, List
import io
import numpy as np
import cv2
import logging
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize EasyOCR reader (lazy loading)
_easyocr_reader = None


def get_easyocr_reader():
    """Lazy load EasyOCR reader with GPU support"""
    global _easyocr_reader
    if _easyocr_reader is None:
        # Check if CUDA is available for GPU acceleration
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
                logger.info(f"CUDA version: {torch.version.cuda}")
            else:
                logger.info("No GPU detected, using CPU for OCR")
        except ImportError:
            gpu_available = False
            logger.warning("PyTorch not found, using CPU for OCR")
        
        _easyocr_reader = easyocr.Reader(['en'], gpu=gpu_available, verbose=False)
        logger.info(f"EasyOCR initialized with GPU={'enabled' if gpu_available else 'disabled'}")
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


def calculate_confidence_score(ocr_result: List[Any]) -> Dict[str, float]:
    """
    Calculate real confidence metrics from EasyOCR detail results.
    
    Args:
        ocr_result: List of tuples from reader.readtext(detail=1)
                   Format: [(text, confidence, bbox), ...]
    
    Returns:
        Dictionary with confidence metrics
    """
    if not ocr_result:
        return {
            "average_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "std_deviation": 0.0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "total_detections": 0
        }
    
    confidences = [item[2] for item in ocr_result if len(item) > 2]
    
    if not confidences:
        return {"average_confidence": 0.0, "total_detections": len(ocr_result)}
    
    high_conf = sum(1 for c in confidences if c > 0.8)
    medium_conf = sum(1 for c in confidences if 0.6 <= c <= 0.8)
    low_conf = sum(1 for c in confidences if c < 0.6)
    
    return {
        "average_confidence": float(np.mean(confidences)),
        "min_confidence": float(np.min(confidences)),
        "max_confidence": float(np.max(confidences)),
        "std_deviation": float(np.std(confidences)),
        "high_confidence_count": high_conf,
        "medium_confidence_count": medium_conf,
        "low_confidence_count": low_conf,
        "total_detections": len(confidences)
    }


def run_easyocr(image: Image.Image) -> Tuple[str, float, Dict[str, Any]]:
    """
    Run EasyOCR and return text with confidence metrics.
    
    Returns:
        Tuple of (extracted_text, heuristic_score, confidence_metrics_dict)
    """
    reader = get_easyocr_reader()
    img_array = np.array(image)
    
    # Get detailed results with confidence scores
    result_detailed = reader.readtext(img_array, detail=1, paragraph=False)
    
    # Extract text
    if isinstance(result_detailed, list):
        text = "\n".join([item[1] for item in result_detailed])
    else:
        text = str(result_detailed or "")
    
    # Calculate both heuristic and real confidence
    heuristic_score = score_extracted_text(text)
    confidence_metrics = calculate_confidence_score(result_detailed)
    
    return text.strip(), heuristic_score, confidence_metrics


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
) -> Dict[str, Any]:
    """
    Extract text from image using EasyOCR with multi-strategy preprocessing.
    Now returns comprehensive accuracy metrics.
    
    Args:
        image_bytes: Image file bytes
        ocr_engine: Not used, kept for API compatibility
    
    Returns:
        Dict with extracted text and detailed OCR accuracy metrics
    """
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Strategy 1: Original image
        text_original, score_original, conf_original = run_easyocr(image)
        logger.info(f"Original image OCR (heuristic_score={score_original:.2f}, avg_confidence={conf_original.get('average_confidence', 0):.3f})")
        
        # Strategy 2: Preprocessed image
        preprocessed_image = preprocess_image_for_ocr(image)
        text_preprocessed, score_preprocessed, conf_preprocessed = run_easyocr(preprocessed_image)
        logger.info(f"Preprocessed image OCR (heuristic_score={score_preprocessed:.2f}, avg_confidence={conf_preprocessed.get('average_confidence', 0):.3f})")
        
        # Choose the best result based on average confidence (real score), then heuristic
        avg_conf_original = conf_original.get('average_confidence', 0)
        avg_conf_preprocessed = conf_preprocessed.get('average_confidence', 0)
        
        if avg_conf_preprocessed > avg_conf_original:
            selected_text = text_preprocessed.strip()
            selected_heuristic = score_preprocessed
            selected_confidence = conf_preprocessed
            selected_strategy = "preprocessed"
            logger.info(f"Selected preprocessed (confidence={avg_conf_preprocessed:.3f})")
        else:
            selected_text = text_original.strip()
            selected_heuristic = score_original
            selected_confidence = conf_original
            selected_strategy = "original"
            logger.info(f"Selected original (confidence={avg_conf_original:.3f})")
        
        # Return comprehensive metrics
        return {
            "text": selected_text,
            "strategy_used": selected_strategy,
            "metrics": {
                "heuristic_score": selected_heuristic,
                "confidence_metrics": selected_confidence,
                "text_length": len(selected_text),
                "comparison": {
                    "original": {
                        "heuristic_score": score_original,
                        "confidence": conf_original.get('average_confidence', 0),
                        "text_length": len(text_original)
                    },
                    "preprocessed": {
                        "heuristic_score": score_preprocessed,
                        "confidence": conf_preprocessed.get('average_confidence', 0),
                        "text_length": len(text_preprocessed)
                    }
                }
            }
        }
    
    except Exception as e:
        logger.error(f"OCR extraction error: {e}", exc_info=True)
        raise Exception(f"Failed to extract text from image: {str(e)}")


async def extract_text_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract text from PDF file with accuracy metrics per page.
    
    Args:
        pdf_bytes: PDF file bytes
    
    Returns:
        Dict with extracted text and per-page accuracy metrics
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
            page_metrics = []
            
            for i, image in enumerate(images):
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                page_result = await extract_text_from_image(buffer.getvalue())
                
                page_text = page_result["text"]
                page_metrics_data = page_result["metrics"]
                
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                page_metrics.append({
                    "page": i+1,
                    "metrics": page_metrics_data
                })
            
            # Calculate overall metrics across all pages
            avg_confidence = np.mean([pm["metrics"]["confidence_metrics"].get("average_confidence", 0) for pm in page_metrics])
            
            return {
                "text": "\n\n".join(text_parts).strip(),
                "total_pages": len(images),
                "metrics": {
                    "overall_average_confidence": float(avg_confidence),
                    "pages": page_metrics
                }
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

