import camelot
import fitz  # PyMuPDF
import re
import os
import tempfile
import requests
from urllib.parse import urlparse
from typing import List, Union, Optional, Tuple

def download_and_extract_text(doc_path: Union[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Download and extract text from one or multiple PDF documents.
    Returns tuple of (table_text, fallback_text) combined from all documents.
    
    Args:
        doc_path: Either a single path/URL or list of paths/URLs
        
    Returns:
        Tuple containing:
        - Combined table text from all documents (or None)
        - Combined fallback text from all documents (or None)
    """
    if isinstance(doc_path, str):
        doc_paths = [doc_path]
    else:
        doc_paths = doc_path

    all_table_text = []
    all_fallback_text = []
    temp_files = []
    
    for path in doc_paths:
        try:
            local_path = None
            if is_url(path):
                print(f"🌐 Downloading document from URL: {path}")
                local_path = download_document(path)
                if not local_path:
                    continue
                temp_files.append(local_path)
            else:
                print(f"📂 Using local file path: {path}")
                if not validate_local_file(path):
                    continue
                local_path = path

            # Process the document
            table_text = extract_structured_table_with_fallback(local_path)
            fallback_text = extract_text_and_urls_fallback(local_path)
            
            if table_text:
                all_table_text.append(f"--- Document: {os.path.basename(path)} ---\n{table_text}")
            if fallback_text:
                all_fallback_text.append(f"--- Document: {os.path.basename(path)} ---\n{fallback_text}")

        except Exception as e:
            print(f"❌ Error processing document {path}: {str(e)}")
            continue

    # Clean up temporary files
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except:
            pass

    combined_table = "\n\n".join(all_table_text) if all_table_text else None
    combined_fallback = "\n\n".join(all_fallback_text) if all_fallback_text else None
    
    return combined_table, combined_fallback

def download_document(url: str) -> Optional[str]:
    """
    Download a PDF document from a URL with robust error handling.
    
    Args:
        url: URL of the PDF to download
        
    Returns:
        Path to downloaded temporary file, or None if failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/pdf'
    }
    
    try:
        # Verify URL points to a PDF
        if not url.lower().endswith('.pdf'):
            head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            content_type = head_response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type:
                print(f"❌ URL doesn't point to a PDF (Content-Type: {content_type})")
                return None
        
        # Download the file
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Verify content is PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type:
            print(f"❌ Downloaded content is not PDF (Content-Type: {content_type})")
            return None
            
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp_file.write(chunk)
            local_path = tmp_file.name
            
        print(f"✅ Downloaded {os.path.getsize(local_path)/1024:.1f} KB to {local_path}")
        return local_path
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed for {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error downloading {url}: {str(e)}")
        return None

def validate_local_file(path: str) -> bool:
    """
    Validate a local PDF file exists and is accessible.
    
    Args:
        path: Local file path
        
    Returns:
        bool: True if valid PDF, False otherwise
    """
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return False
        
    if not path.lower().endswith('.pdf'):
        print(f"❌ File is not PDF: {path}")
        return False
        
    try:
        # Quick check if file is a valid PDF
        with fitz.open(path) as doc:
            if not doc.page_count:
                print(f"❌ PDF appears to be empty: {path}")
                return False
        return True
    except:
        print(f"❌ File is not a valid PDF: {path}")
        return False

def is_url(path: str) -> bool:
    """Check if the path is a valid URL"""
    try:
        parsed = urlparse(path)
        return parsed.scheme in ("http", "https") and parsed.netloc
    except:
        return False

def clean_table(table) -> List[List[str]]:
    """Clean and filter table rows"""
    rows = []
    for row in table.df.values.tolist():
        cleaned = [str(cell).strip() for cell in row if cell is not None]
        if len(cleaned) >= 2 and any(cell for cell in cleaned):
            rows.append(cleaned)
    return rows

def extract_urls(text: str) -> List[str]:
    """Extract all unique URLs from text"""
    url_pattern = r"https?://[^\s)\]]+"  # Match http/https links
    return list(set(re.findall(url_pattern, text)))

def extract_structured_table_with_fallback(pdf_path: str) -> Optional[str]:
    """
    Extract structured tables from PDF with tier detection.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Formatted table text if successful, None otherwise
    """
    def detect_tier_from_amounts(row: List[str]) -> Optional[str]:
        """Detect insurance tier from numerical amounts in row"""
        joined = " ".join(row).replace(",", "")
        amounts = re.findall(r"\d{2,7}", joined)
        if not amounts:
            return None
            
        amounts = list(map(int, amounts))
        
        # Tier detection logic
        if any(a in [25000, 100000, 200000] for a in amounts):
            return "3L/4L/5L"
        elif any(a in [50000, 175000, 350000] for a in amounts):
            return "10L/15L/20L"
        elif any(a in [75000, 250000, 500000] for a in amounts):
            return ">20L"
        return None

    try:
        print(f"📑 Extracting tables from: {pdf_path}")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

        all_rows = []
        sublimit_rows = []
        found_urls = set()

        # Process all tables found in the document
        for table in tables:
            cleaned = clean_table(table)
            if cleaned:
                all_rows.extend(cleaned)

        # Analyze rows for insurance tiers
        for row in all_rows:
            row_clean = [c.strip().replace("`", "").replace("\n", " ") for c in row]
            tier = detect_tier_from_amounts(row_clean)
            if tier:
                row_clean.insert(0, tier)
                if len(row_clean) >= 3:  # Ensure we have at least tier + two data columns
                    sublimit_rows.append(row_clean)
            
            # Extract URLs from table cells
            found_urls.update(extract_urls(" ".join(row)))

        if not sublimit_rows:
            raise ValueError("No relevant table rows found with tier information")

        # Format output
        output = "\n".join([" | ".join(r) for r in sublimit_rows])
        
        if found_urls:
            output += "\n\n🔗 URLs:\n" + "\n".join(sorted(found_urls))

        print(f"\n📊 Extracted {len(sublimit_rows)} table rows from {pdf_path}")
        if len(sublimit_rows) > 5:
            print("First 5 rows:")
            for row in sublimit_rows[:5]:
                print(" | ".join(row))
            print(f"... plus {len(sublimit_rows)-5} more rows")
        else:
            for row in sublimit_rows:
                print(" | ".join(row))

        return output

    except Exception as e:
        print(f"❌ Table extraction failed for {pdf_path}: {str(e)}")
        return None

def extract_text_and_urls_fallback(pdf_path: str) -> Optional[str]:
    """
    Fallback text extraction using PyMuPDF when table extraction fails.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text with URLs if successful, None otherwise
    """
    try:
        text = ""
        urls = set()
        
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text
                    urls.update(extract_urls(page_text))

        if not text.strip():
            return None

        output = text.strip()
        if urls:
            output += "\n\n🔗 URLs:\n" + "\n".join(sorted(urls))

        print(f"\n📝 Extracted {len(text)} characters from {pdf_path}")
        print("Sample text (first 300 chars):", text[:300] + ("..." if len(text) > 300 else ""))
        
        if urls:
            print(f"🔗 Found {len(urls)} URLs in document")

        return output

    except Exception as e:
        print(f"❌ Fallback text extraction failed for {pdf_path}: {str(e)}")
        return None