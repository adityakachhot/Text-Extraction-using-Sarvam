import os
from typing import List
from pypdf import PdfReader, PdfWriter
from app.utils.logging_config import logger

def get_pdf_page_count(pdf_path: str) -> int:
    """Returns the total number of pages in a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        logger.error(f"Failed to read PDF page count from {pdf_path}: {e}")
        raise ValueError(f"Invalid PDF file: {pdf_path}. Details: {e}")

def split_pdf(pdf_path: str, output_dir: str, chunk_size: int = 10) -> List[str]:
    """
    Splits a PDF into smaller sub-PDFs of up to chunk_size pages.
    Returns the list of paths of the split PDF files.
    """
    os.makedirs(output_dir, exist_ok=True)
    total_pages = get_pdf_page_count(pdf_path)
    
    if total_pages <= chunk_size:
        return [pdf_path]
        
    logger.info(f"PDF {pdf_path} has {total_pages} pages. Splitting into chunks of {chunk_size}...")
    reader = PdfReader(pdf_path)
    split_files = []
    
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        end_page = min(i + chunk_size, total_pages)
        
        for page_idx in range(i, end_page):
            writer.add_page(reader.pages[page_idx])
            
        chunk_path = os.path.join(output_dir, f"{base_name}_part_{i//chunk_size + 1}.pdf")
        with open(chunk_path, "wb") as f:
            writer.write(f)
            
        split_files.append(chunk_path)
        logger.info(f"Created split PDF chunk: {chunk_path} (Pages {i+1} to {end_page})")
        
    return split_files
