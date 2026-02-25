#!/usr/bin/env python3
"""
Extract text from a PDF file using pdfplumber.
Usage: python3 extract_text.py <input.pdf> <output.txt>
"""
import sys
import os

def extract_text(pdf_path, output_path):
    try:
        import pdfplumber
    except ImportError:
        os.system("pip install pdfplumber --break-system-packages -q")
        import pdfplumber

    print(f"Extracting text from: {pdf_path}")
    all_text = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                all_text.append(f"\n{'='*80}\nPAGE {i+1}\n{'='*80}\n")
                all_text.append(text)

            if (i + 1) % 20 == 0:
                print(f"  Processed {i+1}/{total_pages} pages...")

    full_text = "\n".join(all_text)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    word_count = len(full_text.split())
    print(f"Extracted {word_count} words to {output_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 extract_text.py <input.pdf> <output.txt>")
        sys.exit(1)
    extract_text(sys.argv[1], sys.argv[2])
