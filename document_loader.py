# document_loader.py
import fitz  # PyMuPDF
import requests
import os

def download_and_extract_text(path_or_url, save_path="policy.pdf"):
    # If it's a URL, download it
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        response = requests.get(path_or_url)
        with open(save_path, "wb") as f:
            f.write(response.content)
        filepath = save_path
    else:
        filepath = path_or_url  # Use local file directly

    # Extract text from PDF
    doc = fitz.open(filepath)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text
