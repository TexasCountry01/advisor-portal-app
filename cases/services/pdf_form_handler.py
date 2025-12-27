"""
Handle PDF form field operations using pypdf library
"""
import os
import logging
from pypdf import PdfReader, PdfWriter
from io import BytesIO

logger = logging.getLogger(__name__)


def get_pdf_form_fields(pdf_path):
    """
    Extract form field names and types from a PDF.
    
    Returns:
        dict: Mapping of field names to field information
    """
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if not fields:
            logger.warning(f"No form fields found in {pdf_path}")
            return {}
        
        field_info = {}
        for field_name, field_obj in fields.items():
            field_type = field_obj.get('/FT', 'Unknown')
            field_info[field_name] = {
                'type': field_type,
                'value': field_obj.get('/V', '')
            }
        
        logger.info(f"Found {len(field_info)} form fields in PDF")
        return field_info
    
    except Exception as e:
        logger.error(f"Error extracting PDF form fields: {str(e)}")
        return {}


def fill_pdf_form(pdf_path, field_values):
    """
    Fill PDF form fields with provided values.
    
    Args:
        pdf_path (str): Path to the reference PDF
        field_values (dict): Dictionary of field_name -> value mappings
    
    Returns:
        BytesIO: Filled PDF as bytes
    """
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Append pages (this preserves the form structure better than add_page)
        writer.append_pages_from_reader(reader)
        
        # Update form field values
        form = writer.get_fields()
        if form:
            for field_name in form:
                if field_name in field_values:
                    try:
                        writer[field_name] = field_values[field_name]
                    except Exception as e:
                        logger.warning(f"Could not set field '{field_name}': {str(e)}")
        
        # Write to BytesIO
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        
        logger.info(f"Successfully filled PDF with {len(field_values)} field values")
        return output
    
    except Exception as e:
        logger.error(f"Error filling PDF form: {str(e)}")
        return None


def extract_pdf_field_values(pdf_bytes):
    """
    Extract current field values from a filled PDF.
    
    Args:
        pdf_bytes (BytesIO or bytes): PDF content
    
    Returns:
        dict: Current field values in the PDF
    """
    try:
        if isinstance(pdf_bytes, bytes):
            pdf_bytes = BytesIO(pdf_bytes)
        
        reader = PdfReader(pdf_bytes)
        fields = reader.get_fields()
        
        if not fields:
            return {}
        
        field_values = {}
        for field_name, field_obj in fields.items():
            field_values[field_name] = field_obj.get('/V', '')
        
        logger.info(f"Extracted {len(field_values)} field values from PDF")
        return field_values
    
    except Exception as e:
        logger.error(f"Error extracting field values: {str(e)}")
        return {}
