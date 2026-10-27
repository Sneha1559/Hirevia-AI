
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract readable text from a PDF resume.

    Args:
        pdf_bytes: The PDF file contents as bytes.

    Returns:
        Extracted text as a string.

    Raises:
        ValueError: If the file is empty, invalid, encrypted,
                    or contains no extractable text.
    """
    if not pdf_bytes:
        raise ValueError("The uploaded PDF file is empty.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)

        if reader.is_encrypted:
            raise ValueError(
                "This PDF is password-protected. "
                "Please upload an accessible PDF."
            )

        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()
            except Exception as exc:
                raise ValueError(
                    f"Could not extract text from PDF page "
                    f"{page_number}."
                ) from exc

            if page_text and page_text.strip():
                extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages).strip()

        if not full_text:
            raise ValueError(
                "No extractable text was found. "
                "The PDF may contain scanned images; OCR support "
                "will be considered in a later step."
            )

        return full_text

    except ValueError:
        raise

    except PdfReadError as exc:
        raise ValueError(
            "The file is not a readable PDF. Please check the file."
        ) from exc

    except Exception as exc:
        raise ValueError(
            "An unexpected error occurred while reading the PDF."
        ) from exc
