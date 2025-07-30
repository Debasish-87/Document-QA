import camelot
import fitz  # PyMuPDF
import re
import os

def clean_table(table):
    rows = []
    for row in table.df.values.tolist():
        # Strip whitespace and drop rows with only one filled cell
        cleaned = [cell.strip() for cell in row]
        if sum([bool(c) for c in cleaned]) >= 2:
            rows.append(cleaned)
    return rows

def extract_structured_table_with_fallback(pdf_path):
    try:
        print("📑 Extracting table (Camelot)...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

        all_rows = []
        for table in tables:
            all_rows.extend(clean_table(table))

        sublimit_rows = []
        for row in all_rows:
            if any("Robotic" in c or "cancer" in c.lower() or "cataract" in c.lower() for c in row):
                sublimit_rows.append(row)

        print("\n📑 DEBUG: Filtered Table Rows:")
        for r in sublimit_rows:
            print(r)

        return "\n".join([" | ".join(r) for r in sublimit_rows]) if sublimit_rows else None

    except Exception as e:
        print("❌ Camelot extraction failed. Falling back to text:", e)
        return None

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text
