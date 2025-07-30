import camelot
import fitz  # PyMuPDF
import re
import os
import tempfile
import requests
from urllib.parse import urlparse

def download_and_extract_text(doc_path):
    if is_url(doc_path):
        print("🌐 Detected URL. Downloading...")
        response = requests.get(doc_path)
        if response.status_code != 200:
            raise ValueError(f"Failed to download document: {doc_path}")
        
        suffix = ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(response.content)
            local_path = tmp_file.name
        print(f"✅ Downloaded to temp file: {local_path}")
    else:
        print("📂 Detected local file path.")
        local_path = doc_path
    
    return extract_structured_table_with_fallback(local_path)

def is_url(path):
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")

def clean_table(table):
    rows = []
    for row in table.df.values.tolist():
        cleaned = [cell.strip() for cell in row]
        if sum([bool(c) for c in cleaned]) >= 2:
            rows.append(cleaned)
    return rows

def extract_urls(text):
    url_pattern = r"https?://[^\s)\]]+"  # Match http/https links
    return re.findall(url_pattern, text)

def extract_structured_table_with_fallback(pdf_path):
    try:
        print("📑 Extracting table (Camelot)...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

        all_rows = []
        for table in tables:
            all_rows.extend(clean_table(table))

        sublimit_rows = []
        found_urls = set()

        for row in all_rows:
            if any("Robotic" in c or "cancer" in c.lower() or "cataract" in c.lower() for c in row):
                sublimit_rows.append(row)
            for cell in row:
                found_urls.update(extract_urls(cell))

        print("\n📑 DEBUG: Filtered Table Rows:")
        for r in sublimit_rows:
            print(r)

        print("\n🔗 Extracted URLs from tables:")
        for url in found_urls:
            print(url)

        output = "\n".join([" | ".join(r) for r in sublimit_rows])
        if found_urls:
            output += "\n\n🔗 URLs:\n" + "\n".join(sorted(found_urls))

        return output if output.strip() else None

    except Exception as e:
        print("❌ Camelot extraction failed. Falling back to text:", e)
        return extract_text_and_urls_fallback(pdf_path)

def extract_text_and_urls_fallback(pdf_path):
    text = ""
    urls = set()
    with fitz.open(pdf_path) as doc:
        for page in doc:
            page_text = page.get_text()
            text += page_text
            urls.update(extract_urls(page_text))

    print("\n📝 Fallback Extracted Text (Truncated Preview):")
    print(text[:1000])  # Preview first 1000 characters

    print("\n🔗 Extracted URLs from raw text:")
    for url in urls:
        print(url)

    output = text.strip()
    if urls:
        output += "\n\n🔗 URLs:\n" + "\n".join(sorted(urls))

    return output if output.strip() else None
