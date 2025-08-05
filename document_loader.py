import camelot
import fitz  # PyMuPDF
import re
import os
import requests
from urllib.parse import urlparse


def download_and_extract_text(doc_path):
    pdf_dir = "pdf"
    os.makedirs(pdf_dir, exist_ok=True)  # Ensure the 'pdf' directory exists

    if is_url(doc_path):
        print("🌐 Detected URL. Downloading...")
        response = requests.get(doc_path)
        if response.status_code != 200:
            raise ValueError(f"Failed to download document: {doc_path}")

        filename = os.path.basename(urlparse(doc_path).path)
        if not filename.lower().endswith(".pdf"):
            filename = "downloaded_document.pdf"

        local_path = os.path.join(pdf_dir, filename)

        with open(local_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Downloaded to: {local_path}")
    else:
        print("📂 Detected local file path.")
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"File not found: {doc_path}")

        filename = os.path.basename(doc_path)
        local_path = os.path.join(pdf_dir, filename)

        if doc_path != local_path:
            with open(doc_path, "rb") as src, open(local_path, "wb") as dst:
                dst.write(src.read())
            print(f"📁 Copied local file to: {local_path}")
        else:
            print(f"📁 File already in pdf directory: {local_path}")

    return extract_structured_table_with_fallback(local_path)


def is_url(path):
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


def clean_table(table):
    rows = []
    for row in table.df.values.tolist():
        cleaned = [cell.strip() for cell in row]
        if sum(bool(c) for c in cleaned) >= 2:
            rows.append(cleaned)
    return rows


def extract_urls(text):
    url_pattern = r"https?://[^\s)\]]+"  # Match http/https links
    return re.findall(url_pattern, text)


def extract_structured_table_with_fallback(pdf_path):
    def detect_tier_from_amounts(row):
        joined = " ".join(row).replace(",", "")
        amounts = re.findall(r"\d{2,7}", joined)
        if not amounts:
            return None
        amounts = list(map(int, amounts))

        if any(a in [25000, 100000, 200000] for a in amounts):
            return "3L/4L/5L"
        elif any(a in [50000, 175000, 350000] for a in amounts):
            return "10L/15L/20L"
        elif any(a in [75000, 250000, 500000] for a in amounts):
            return ">20L"
        return None

    try:
        print("📑 Extracting table (Camelot)...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

        all_rows = []
        sublimit_rows = []
        found_urls = set()

        for table in tables:
            all_rows.extend(clean_table(table))

        for row in all_rows:
            row_clean = [c.strip().replace("`", "").replace("\n", " ") for c in row]
            tier = detect_tier_from_amounts(row_clean)
            if tier:
                row_clean.insert(0, tier)
                if len(row_clean) >= 3:
                    sublimit_rows.append(row_clean)

            for cell in row:
                found_urls.update(extract_urls(cell))

        print("\n📑 DEBUG: Filtered Table Rows:")
        for r in sublimit_rows:
            print(r)

        print("\n🔗 Extracted URLs from tables:")
        for url in found_urls:
            print(url)

        if sublimit_rows:
            output = "\n".join([" | ".join(r) for r in sublimit_rows])
            if found_urls:
                output += "\n\n🔗 URLs:\n" + "\n".join(sorted(found_urls))

            print("\n📊 Table Data Preview (first 5 rows):")
            for row in sublimit_rows[:5]:
                print(" | ".join(row))

            return output
        else:
            raise ValueError("No relevant table rows found")

    except Exception as e:
        print("❌ Camelot extraction failed or empty. Falling back to text:", e)
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
    print(text[:1000])  # Show first 1000 characters

    print("\n🔗 Extracted URLs from raw text:")
    for url in urls:
        print(url)

    output = text.strip()
    if urls:
        output += "\n\n🔗 URLs:\n" + "\n".join(sorted(urls))

    return output if output.strip() else None
