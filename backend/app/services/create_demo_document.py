"""Generate a synthetic demo identity document image for OCR testing.

This creates a realistic-looking but entirely fictional identity document
with clear text fields that PaddleOCR can extract. No real PII is used.
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_demo_document(output_path: str = None) -> str:
    """Create a synthetic identity document image and return its path."""
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "uploads", "demo_document.png"
        )

    # Card dimensions (standard ID card aspect ratio)
    width, height = 800, 500

    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fall back to default
    try:
        font_large = ImageFont.truetype("arial.ttf", 28)
        font_medium = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 14)
        font_title = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except OSError:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_title = ImageFont.load_default()

    # Header bar
    draw.rectangle([(0, 0), (width, 60)], fill=(0, 15, 34))
    draw.text((20, 15), "REPUBLIC OF INDIA", fill=(255, 255, 255), font=font_title)
    draw.text((width - 200, 20), "SAMPLE DOCUMENT", fill=(200, 200, 200), font=font_small)

    # Sub-header
    draw.rectangle([(0, 60), (width, 95)], fill=(74, 62, 230))
    draw.text((20, 67), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill=(255, 255, 255), font=font_medium)

    # Photo placeholder
    draw.rectangle([(30, 120), (180, 280)], outline=(0, 0, 0), width=2, fill=(230, 230, 240))
    draw.text((70, 180), "PHOTO", fill=(150, 150, 150), font=font_small)

    # Document fields
    y_start = 120
    x_label = 210
    x_value = 380

    fields = [
        ("Name:", "PRIYA SHARMA"),
        ("Date of Birth:", "15-MAR-1995"),
        ("Gender:", "FEMALE"),
        ("Father's Name:", "RAJESH SHARMA"),
        ("Address:", "42 MG Road, Sector 15"),
        ("", "Gurugram, Haryana - 122001"),
        ("ID Number:", "1234-5678-9012"),
    ]

    for i, (label, value) in enumerate(fields):
        y = y_start + i * 32
        if label:
            draw.text((x_label, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((x_value, y), value, fill=(0, 0, 0), font=font_medium)

    # Bottom section
    draw.rectangle([(0, 380), (width, 382)], fill=(200, 200, 200))
    draw.text((30, 395), "Date of Issue: 01-JAN-2020", fill=(80, 80, 80), font=font_small)
    draw.text((300, 395), "Valid Until: 01-JAN-2035", fill=(80, 80, 80), font=font_small)
    draw.text((30, 425), "This is a synthetic sample document for testing purposes only.", fill=(180, 50, 50), font=font_small)
    draw.text((30, 450), "NOT A REAL IDENTITY DOCUMENT", fill=(180, 50, 50), font=font_small)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    path = create_demo_document()
    print(f"Demo document created at: {path}")
