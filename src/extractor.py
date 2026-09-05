import io
import re
import fitz
import docx
import pandas as pd
import pytesseract
from PIL import Image
from typing import Tuple
from src.config import TESSERACT_PATH, MAX_FILE_SIZE, MAX_TEXT_LENGTH
from src.logging_utils import get_logger

# Get logger
logger = get_logger(__name__)

# Configure Tesseract OCR path from centralized config
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# File signature mappings for MIME type detection (magic bytes)
# NOTE: Using a list of tuples because DOCX and XLSX share the same magic bytes (PK\x03\x04)
FILE_SIGNATURES = [
    # PDF signature
    (b'%PDF', 'application/pdf'),
    # PNG signature
    (b'\x89PNG', 'image/png'),
    # JPEG signatures
    (b'\xff\xd8\xff', 'image/jpeg'),
    # DOCX (ZIP-based - PK signature)
    (b'PK\x03\x04', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    # XLSX (ZIP-based — same magic bytes, differentiated by internal structure)
    (b'PK\x03\x04', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    # Text files (UTF-8 BOM)
    (b'\xef\xbb\xbf', 'text/plain'),
    # CSV typically starts with text
]

# Allowed MIME types mapping to extensions
ALLOWED_MIME_TYPES = {
    'application/pdf': ['pdf'],
    'image/png': ['png'],
    'image/jpeg': ['jpg', 'jpeg'],
    'text/plain': ['txt'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['xlsx'],
    'text/csv': ['csv'],
}


def detect_mime_type(file_bytes: bytes) -> str:
    """Detect MIME type from file content using magic bytes.
    
    Args:
        file_bytes: Raw file bytes
        
    Returns:
        Detected MIME type or 'application/octet-stream' if unknown
    """
    if len(file_bytes) < 4:
        return 'application/octet-stream'
    
    # Check for PDF
    if file_bytes.startswith(b'%PDF'):
        return 'application/pdf'
    
    # Check for PNG
    if file_bytes.startswith(b'\x89PNG'):
        return 'image/png'
    
    # Check for JPEG
    if file_bytes[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    
    # Check for ZIP-based formats (DOCX, XLSX)
    if file_bytes.startswith(b'PK\x03\x04'):
        # Try to determine specific format by checking internal structure
        # For now, return generic ZIP - actual validation happens during processing
        return 'application/zip'
    
    # Check for text (UTF-8 BOM)
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        return 'text/plain'
    
    # Try to decode as text
    try:
        file_bytes[:1000].decode('utf-8')
        return 'text/plain'
    except UnicodeDecodeError:
        pass
    
    return 'application/octet-stream'


def validate_mime_type(file_bytes: bytes, expected_ext: str) -> Tuple[bool, str]:
    """Validate that file content matches expected MIME type based on extension.
    
    Args:
        file_bytes: Raw file bytes
        expected_ext: Expected file extension
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    detected_mime = detect_mime_type(file_bytes)
    
    # Map extension to expected MIME type
    ext_to_mime = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'txt': 'text/plain',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
    }
    
    expected_mime = ext_to_mime.get(expected_ext.lower())
    
    if not expected_mime:
        return False, f"Unknown file extension: {expected_ext}"
    
    # Special handling for ZIP-based formats (docx, xlsx)
    if expected_ext.lower() in ['docx', 'xlsx']:
        if detected_mime == 'application/zip' or detected_mime.startswith('application/vnd.openxmlformats'):
            return True, ""
        return False, f"File content does not match {expected_ext} format"
    
    # For other formats, check exact match
    if detected_mime == expected_mime:
        return True, ""
    
    # Special case: text/csv vs text/plain - both acceptable
    if detected_mime == 'text/plain' and expected_mime in ['text/plain', 'text/csv']:
        return True, ""
    
    return False, f"File content ({detected_mime}) does not match expected type ({expected_mime})"


def extract_image_text(image_bytes: bytes) -> str:
    """Extract text from image using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        return f"[OCR Error: {str(e)}]"


def validate_file_size(file_bytes: bytes) -> Tuple[bool, str]:
    """Validate file size against configured limits."""
    if len(file_bytes) > MAX_FILE_SIZE:
        return (
            False,
            f"Error: File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
        )
    return True, ""


def validate_text_length(text: str) -> str:
    """Validate and truncate text if exceeds maximum length."""
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH] + "\n[Content truncated due to size]"
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    return filename


def process_file(uploaded_file) -> Tuple[str, str]:
    """Process uploaded file and extract text content.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Tuple of (sanitized_filename, extracted_text_or_error_message)
    """
    filename = sanitize_filename(uploaded_file.name)
    ext = filename.split(".")[-1].lower()
    text_content = ""
    file_bytes = uploaded_file.read()

    # Validate file size
    is_valid, error_msg = validate_file_size(file_bytes)
    if not is_valid:
        return filename, error_msg
    
    # Validate MIME type to prevent extension spoofing
    is_valid, error_msg = validate_mime_type(file_bytes, ext)
    if not is_valid:
        return filename, error_msg

    try:
        if ext in ["png", "jpg", "jpeg"]:
            text_content = extract_image_text(file_bytes)

        elif ext == "txt":
            text_content = file_bytes.decode("utf-8")
            text_content = validate_text_length(text_content)

        elif ext == "pdf":
            # Use context manager for proper file handle management
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text() + " "
            text_content = validate_text_length(text_content)

        elif ext == "docx":
            # Use context manager for docx
            with docx.Document(io.BytesIO(file_bytes)) as doc:
                text_content = " ".join([p.text for p in doc.paragraphs])
            text_content = validate_text_length(text_content)

        elif ext in ["csv", "xlsx"]:
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            text_content = df.to_string(index=False)
            text_content = validate_text_length(text_content)

        else:
            return filename, f"Unsupported format: {ext}"

    except UnicodeDecodeError:
        return (
            filename,
            "Error: Unable to decode file. Please use UTF-8 encoded text files.",
        )
    except Exception as e:
        return filename, f"Error: {str(e)}"

    return filename, text_content
