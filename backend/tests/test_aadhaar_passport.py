"""Aadhaar and Passport OCR Pipeline Tests.

Tests the simplified OCR pipeline with separate document types:
- Aadhaar: OCR → field extraction (NO MRZ)
- Passport: OCR → MRZ detection → field extraction (MRZ combined)

Uses synthetic document images with known identity data.
"""

import os
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.field_extraction_service import extract_fields
from app.services.mrz_service import detect_mrz, parse_mrz_passport, is_mrz_line
from app.services.image_preprocessing import create_preprocessing_variants

# ---------- Synthetic Document Generators ----------

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")


def _get_font(size: int):
    """Get a font, with fallbacks."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


def create_synthetic_aadhaar(
    output_path: str,
    name: str = "RAJESH KUMAR",
    dob: str = "15/06/1985",
    gender: str = "MALE",
    id_number: str = "1234-5678-9012",
    address_lines: list[str] = None,
    father_name: str = "SURESH KUMAR",
) -> str:
    """Create a synthetic Aadhaar-style identity document image.

    The layout mimics a standard Aadhaar card with clearly labeled fields.
    All values are synthetic — no real PII.
    """
    if address_lines is None:
        address_lines = ["42 MG Road, Sector 15", "Gurugram, Haryana - 122001"]

    width, height = 800, 500
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_title = _get_font(22)
    font_medium = _get_font(18)
    font_small = _get_font(14)
    font_label = _get_font(12)

    # Header bar (Aadhaar-style blue)
    draw.rectangle([(0, 0), (width, 55)], fill=(0, 51, 102))
    draw.text((20, 12), "REPUBLIC OF INDIA", fill=(255, 255, 255), font=font_title)
    draw.text((width - 180, 18), "SAMPLE DOCUMENT", fill=(200, 200, 200), font=font_small)

    # Sub-header
    draw.rectangle([(0, 55), (width, 85)], fill=(74, 62, 230))
    draw.text((20, 61), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill=(255, 255, 255), font=font_medium)

    # Photo placeholder
    draw.rectangle([(30, 105), (170, 260)], outline=(0, 0, 0), width=2, fill=(230, 230, 240))
    draw.text((65, 170), "PHOTO", fill=(150, 150, 150), font=font_small)

    # Document fields
    y_start = 110
    x_label = 200
    x_value = 370
    gap = 30

    fields = [
        ("Name:", name),
        ("Date of Birth:", dob),
        ("Gender:", gender),
        ("Father's Name:", father_name),
        ("ID Number:", id_number),
        ("Address:", address_lines[0]),
    ]
    if len(address_lines) > 1:
        fields.append(("", address_lines[1]))

    for i, (label, value) in enumerate(fields):
        y = y_start + i * gap
        if label:
            draw.text((x_label, y), label, fill=(100, 100, 100), font=font_label)
        draw.text((x_value, y), value, fill=(0, 0, 0), font=font_medium)

    # Bottom bar
    draw.rectangle([(0, height - 60), (width, height - 58)], fill=(200, 200, 200))
    draw.text((30, height - 50), "Date of Issue: 01-JAN-2020", fill=(80, 80, 80), font=font_small)
    draw.text((300, height - 50), "Valid Until: 01-JAN-2035", fill=(80, 80, 80), font=font_small)

    # Warning text
    draw.text((30, height - 25), "SYNTHETIC TEST DOCUMENT — NOT A REAL IDENTITY", fill=(180, 50, 50), font=font_small)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_synthetic_passport(
    output_path: str,
    surname: str = "SHARMA",
    given_names: str = "ANANYA",
    passport_no: str = "R98765432",
    nationality: str = "IND",
    dob_yymmdd: str = "920714",
    sex: str = "F",
    expiry_yymmdd: str = "320713",
) -> str:
    """Create a synthetic passport page with visible text AND MRZ.

    Uses TD3 MRZ format (44 chars per line).
    """
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(245, 245, 250))
    draw = ImageDraw.Draw(img)

    font_title = _get_font(20)
    font_medium = _get_font(16)
    font_small = _get_font(12)

    try:
        font_mrz = ImageFont.truetype("cour.ttf", 14)
    except OSError:
        try:
            font_mrz = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
        except OSError:
            font_mrz = _get_font(14)

    # Header
    draw.rectangle([(0, 0), (width, 50)], fill=(0, 51, 102))
    draw.text((20, 12), "REPUBLIC OF INDIA", fill=(255, 255, 255), font=font_title)
    draw.text((width - 120, 16), "PASSPORT", fill=(200, 200, 200), font=font_small)

    # Identity fields
    y = 70
    gap = 28

    # Format DOB from YYMMDD to readable
    dob_yy = int(dob_yymmdd[:2])
    dob_mm = int(dob_yymmdd[2:4])
    dob_dd = int(dob_yymmdd[4:6])
    dob_year = 1900 + dob_yy if dob_yy > 30 else 2000 + dob_yy
    dob_readable = f"{dob_dd:02d}/{dob_mm:02d}/{dob_year}"

    fields = [
        ("Surname:", surname),
        ("Given Names:", given_names),
        ("Passport No.:", passport_no),
        ("Nationality:", nationality),
        ("Date of Birth:", dob_readable),
        ("Sex:", sex),
    ]

    for label, value in fields:
        draw.text((30, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((170, y), value, fill=(0, 0, 0), font=font_medium)
        y += gap

    # MRZ at bottom (TD3 format)
    name_mrz = f"P<IND{surname.upper()}<<{given_names.upper()}"
    name_mrz = name_mrz.ljust(44, "<")

    line2 = f"{passport_no:<9}{nationality.upper()}{dob_yymmdd}{sex}{expiry_yymmdd}"
    line2 = line2.ljust(44, "<")

    draw.rectangle([(0, height - 80), (width, height)], fill=(230, 230, 240))
    draw.text((20, height - 70), name_mrz, fill=(0, 0, 0), font=font_mrz)
    draw.text((20, height - 48), line2, fill=(0, 0, 0), font=font_mrz)

    # Warning text
    draw.text((20, height - 20), "SYNTHETIC TEST DOCUMENT — NOT A REAL PASSPORT", fill=(180, 50, 50), font=font_small)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


# ---------- Aadhaar Tests ----------

AADHAAR_IMAGE = os.path.join(UPLOADS_DIR, "test_aadhaar.png")


@pytest.fixture(scope="module", autouse=True)
def create_aadhaar_image():
    """Create a synthetic Aadhaar image once for all Aadhaar tests."""
    create_synthetic_aadhaar(
        AADHAAR_IMAGE,
        name="RAJESH KUMAR",
        dob="15/06/1985",
        gender="MALE",
        id_number="1234-5678-9012",
        address_lines=["42 MG Road, Sector 15", "Gurugram, Haryana - 122001"],
        father_name="SURESH KUMAR",
    )
    yield
    # Cleanup is optional


class TestAadhaarFieldExtraction:
    """Test field extraction from Aadhaar-style OCR output."""

    def test_name_extraction(self):
        """Name field should be extracted from labeled OCR lines."""
        ocr_lines = [
            {"text": "REPUBLIC OF INDIA", "confidence": 0.95},
            {"text": "Name:", "confidence": 0.93},
            {"text": "RAJESH KUMAR", "confidence": 0.97},
            {"text": "Date of Birth:", "confidence": 0.92},
            {"text": "15/06/1985", "confidence": 0.96},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["full_name"] == "RAJESH KUMAR"

    def test_dob_extraction(self):
        """DOB should be extracted and normalized to ISO format."""
        ocr_lines = [
            {"text": "Date of Birth:", "confidence": 0.92},
            {"text": "15/06/1985", "confidence": 0.96},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["date_of_birth"] == "1985-06-15"

    def test_dob_inline_extraction(self):
        """DOB on same line as label."""
        ocr_lines = [
            {"text": "Date of Birth: 15/06/1985", "confidence": 0.94},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["date_of_birth"] == "1985-06-15"

    def test_gender_extraction(self):
        """Gender should be extracted from labeled or standalone lines."""
        ocr_lines = [
            {"text": "Gender:", "confidence": 0.93},
            {"text": "MALE", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["gender"] == "MALE"

    def test_gender_fallback(self):
        """Gender should be detected as standalone word."""
        ocr_lines = [
            {"text": "RAJESH KUMAR", "confidence": 0.97},
            {"text": "MALE", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["gender"] == "MALE"

    def test_id_number_extraction(self):
        """ID number with dashes should be extracted."""
        ocr_lines = [
            {"text": "ID Number:", "confidence": 0.91},
            {"text": "1234-5678-9012", "confidence": 0.95},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["document_number"] == "1234-5678-9012"

    def test_address_extraction(self):
        """Multi-line address should be combined."""
        ocr_lines = [
            {"text": "Address:", "confidence": 0.90},
            {"text": "42 MG Road, Sector 15", "confidence": 0.93},
            {"text": "Gurugram, Haryana - 122001", "confidence": 0.92},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["address"] is not None
        assert "42 MG Road" in result["address"]
        assert "Gurugram" in result["address"]

    def test_father_name_extraction(self):
        """Father's name should be extracted."""
        ocr_lines = [
            {"text": "Father's Name:", "confidence": 0.91},
            {"text": "SURESH KUMAR", "confidence": 0.96},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["father_name"] == "SURESH KUMAR"

    def test_aadhaar_no_mrz_invoked(self):
        """Aadhaar processing should NOT invoke MRZ detection."""
        ocr_lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "TEST USER", "confidence": 0.97},
        ]
        # MRZ should be None (not invoked) for Aadhaar
        result = extract_fields(ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "TEST USER"
        assert result.get("field_status", {}).get("full_name") == "extracted"

    def test_missing_fields_return_none(self):
        """Unextracted fields should return None."""
        ocr_lines = [
            {"text": "Random unrelated text", "confidence": 0.80},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["document_number"] is None
        assert result["gender"] is None

    def test_field_status_populated(self):
        """field_status should track extraction status."""
        ocr_lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "TEST USER", "confidence": 0.97},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")
        assert result["field_status"]["full_name"] == "extracted"
        assert result["field_status"]["date_of_birth"] == "not_detected"


class TestAadhaarPreprocessing:
    """Test that preprocessing works for Aadhaar documents."""

    def test_preprocessing_creates_two_variants(self):
        """Should create exactly 2 preprocessing variants."""
        if not os.path.exists(AADHAAR_IMAGE):
            pytest.skip("Test Aadhaar image not created")

        result = create_preprocessing_variants(AADHAAR_IMAGE, document_type="aadhaar")
        variants = result.get("variants", [])
        assert len(variants) == 2
        names = [v["name"] for v in variants]
        assert "preprocessed" in names
        assert "gray_contrast" in names

    def test_no_aggressive_transforms(self):
        """Should NOT include threshold, denoise_sharpen, or morphological."""
        if not os.path.exists(AADHAAR_IMAGE):
            pytest.skip("Test Aadhaar image not created")

        result = create_preprocessing_variants(AADHAAR_IMAGE)
        names = [v["name"] for v in result.get("variants", [])]
        assert "threshold" not in names
        assert "denoise_sharpen" not in names
        assert "morphological" not in names


class TestAadhaarDocumentIsolation:
    """Verify no stale data leaks between Aadhaar analyses."""

    def test_different_aadhaar_names(self):
        """Two different Aadhaar analyses should produce different names."""
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
            {"text": "Date of Birth:", "confidence": 0.93},
            {"text": "14/03/1995", "confidence": 0.97},
        ]
        result_a = extract_fields(lines_a, document_type="aadhaar")

        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "AMIT SINGH", "confidence": 0.99},
            {"text": "Date of Birth:", "confidence": 0.92},
            {"text": "22/11/1990", "confidence": 0.96},
        ]
        result_b = extract_fields(lines_b, document_type="aadhaar")

        assert result_a["full_name"] == "PRIYA SHARMA"
        assert result_b["full_name"] == "AMIT SINGH"
        assert result_a["date_of_birth"] == "1995-03-14"
        assert result_b["date_of_birth"] == "1990-11-22"

    def test_no_previous_result_leakage(self):
        """Analyzing document B after A should not carry A's values."""
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
            {"text": "ID Number:", "confidence": 0.93},
            {"text": "1234-5678-9012", "confidence": 0.97},
        ]
        extract_fields(lines_a, document_type="aadhaar")

        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "AMIT SINGH", "confidence": 0.99},
            {"text": "ID Number:", "confidence": 0.94},
            {"text": "9999-8888-7777", "confidence": 0.98},
        ]
        result_b = extract_fields(lines_b, document_type="aadhaar")

        assert result_b["full_name"] == "AMIT SINGH"
        assert result_b["document_number"] == "9999-8888-7777"
        assert result_b["full_name"] != "PRIYA SHARMA"
        assert result_b["document_number"] != "1234-5678-9012"


# ---------- Passport / MRZ Tests ----------

PASSPORT_IMAGE = os.path.join(UPLOADS_DIR, "test_passport.png")


@pytest.fixture(scope="module", autouse=True)
def create_passport_image():
    """Create a synthetic passport image once for all passport tests."""
    create_synthetic_passport(
        PASSPORT_IMAGE,
        surname="SHARMA",
        given_names="ANANYA",
        passport_no="R98765432",
        nationality="IND",
        dob_yymmdd="920714",
        sex="F",
        expiry_yymmdd="320713",
    )
    yield


class TestMRZDetection:
    """Test MRZ line detection from OCR output."""

    def test_valid_mrz_lines_detected(self):
        """Two consecutive MRZ-like lines should be detected."""
        ocr_lines = [
            {"text": "REPUBLIC OF INDIA", "confidence": 0.95},
            {"text": "PASSPORT", "confidence": 0.93},
            {"text": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<<", "confidence": 0.90},
            {"text": "R987654322IND9207142F3207130<<<<<<<<<<<<06", "confidence": 0.88},
        ]
        mrz = detect_mrz(ocr_lines)
        assert mrz["detected"] is True
        assert mrz["line1"] is not None
        assert mrz["line2"] is not None

    def test_no_mrz_when_absent(self):
        """No MRZ detection when lines are regular text."""
        ocr_lines = [
            {"text": "Name: JOHN DOE", "confidence": 0.95},
            {"text": "DOB: 01/01/1990", "confidence": 0.93},
        ]
        mrz = detect_mrz(ocr_lines)
        assert mrz["detected"] is False

    def test_mrz_line_length_check(self):
        """MRZ lines must be at least 25 chars."""
        assert is_mrz_line("SHORT") is False
        assert is_mrz_line("P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<<") is True


class TestMRZParsing:
    """Test TD3 passport MRZ parsing."""

    def test_parse_passport_mrz_fields(self):
        """Parse passport MRZ and extract all fields."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        fields = parse_mrz_passport(mrz_data)

        assert fields["surname"] == "Sharma"
        assert fields["given_names"] == "Ananya"
        assert fields["nationality"] == "IND"
        assert fields["sex"] == "F"
        assert fields["date_of_birth"] == "1992-07-14"
        assert fields["date_of_expiry"] == "2032-07-13"

    def test_parse_mrz_passport_number(self):
        """Passport number should be extracted from MRZ line 2."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is not None
        assert len(fields["passport_number"]) >= 6

    def test_parse_mrz_not_detected(self):
        """When MRZ not detected, all fields should be None."""
        mrz_data = {"detected": False, "line1": None, "line2": None, "confidence": None}
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is None
        assert fields["surname"] is None


class TestPassportFieldExtraction:
    """Test passport field extraction with MRZ data."""

    def test_passport_uses_mrz_for_surname(self):
        """Passport surname should come from MRZ."""
        ocr_lines = [
            {"text": "PASSPORT", "confidence": 0.93},
            {"text": "SHARMA", "confidence": 0.90},
        ]
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)
        assert result["surname"] == "Sharma"
        assert result["given_names"] == "Ananya"

    def test_passport_mrz_dob(self):
        """Passport DOB should come from MRZ."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        result = extract_fields([], document_type="passport", mrz_data=mrz_data)
        assert result["date_of_birth"] == "1992-07-14"

    def test_passport_mrz_gender(self):
        """Passport gender should come from MRZ sex field."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        result = extract_fields([], document_type="passport", mrz_data=mrz_data)
        assert result["gender"] == "F"

    def test_passport_mrz_nationality(self):
        """Nationality should come from MRZ."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        result = extract_fields([], document_type="passport", mrz_data=mrz_data)
        assert result["nationality"] == "IND"

    def test_passport_document_type_detected(self):
        """Document type should be 'passport' when MRZ starts with P."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654322IND9207142F3207130<<<<<<<<<<<<06",
            "confidence": 0.89,
        }
        result = extract_fields([], document_type=None, mrz_data=mrz_data)
        assert result["document_type"] == "passport"


class TestPassportDocumentIsolation:
    """Verify passport MRZ data is isolated per analysis."""

    def test_different_passports_different_names(self):
        """Two different passport MRZs should produce different names."""
        mrz_a = {
            "detected": True,
            "line1": "P<INDKUMAR<<RAVI<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "Y123456784IND8506152M3012315<<<<<<<<<<<<<04",
            "confidence": 0.92,
        }
        result_a = extract_fields([], document_type="passport", mrz_data=mrz_a)

        mrz_b = {
            "detected": True,
            "line1": "P<INDPATEL<<NITIN<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "Z987654324IND9001152F2812310<<<<<<<<<<<<<06",
            "confidence": 0.88,
        }
        result_b = extract_fields([], document_type="passport", mrz_data=mrz_b)

        assert result_a["surname"] == "Kumar"
        assert result_a["given_names"] == "Ravi"
        assert result_b["surname"] == "Patel"
        assert result_b["given_names"] == "Nitin"
        assert result_a["document_number"] != result_b["document_number"]
