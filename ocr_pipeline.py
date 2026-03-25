import base64
import io
import os

import fitz  # pymupdf — no poppler needed on Windows
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def page_to_base64(page) -> str:
    """Render a pymupdf page to a PNG and return as base64."""
    # Render at 2x scale for clarity (good for handwriting/diagrams)
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")


def extract_text_from_page(page, page_num: int) -> str:
    """Send one page image to Groq vision and get back extracted text."""
    
    # First try fast text extraction (works on text-based PDFs)
    direct_text = page.get_text().strip()
    if len(direct_text) > 50:
        print(f"  Page {page_num}: extracted {len(direct_text)} chars (direct text)")
        return direct_text

    # Fallback to Groq vision OCR for image-based / scanned pages
    print(f"  Page {page_num}: no direct text, using Groq vision OCR...")
    b64 = page_to_base64(page)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    },
                    {
                        "type": "text",
                        "text": (
                            "Transcribe ALL text from this page exactly as it appears. "
                            "Include both printed text and handwritten text. "
                            "Preserve the structure — headings, bullet points, paragraphs. "
                            "If there are diagrams with labels, include those labels too. "
                            "Output only the transcribed text, nothing else."
                        )
                    }
                ]
            }
        ],
        max_tokens=2000,
    )

    text = response.choices[0].message.content.strip()
    print(f"  Page {page_num}: extracted {len(text)} chars (OCR)")
    return text


def pdf_to_text_via_ocr(pdf_path: str) -> list:
    """
    Convert a PDF to a list of {page_content, metadata} dicts.
    Uses direct text extraction for text PDFs, Groq vision OCR for scanned/image PDFs.
    """
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"  {len(doc)} pages found...")

    documents = []
    for i, page in enumerate(doc):
        text = extract_text_from_page(page, i + 1)
        if text:  # skip blank pages
            documents.append({
                "page_content": text,
                "metadata": {
                    "page": i + 1,
                    "source": pdf_path
                }
            })

    doc.close()
    print(f"Done: {len(documents)} pages with text extracted")
    return documents