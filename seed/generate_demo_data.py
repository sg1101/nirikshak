"""Generate mock bidder PDFs for demo. Run from project root: python seed/generate_demo_data.py"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _pdf(path, pages_fn):
    c = canvas.Canvas(str(path), pagesize=A4)
    pages_fn(c)
    c.save()


def _header(c, title, y=780):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(150, y, title)
    c.setFont("Helvetica", 11)


def make_gst_cert(out: Path, gstin: str, name: str, status="Active", reg_date="01-07-2017"):
    def draw(c):
        _header(c, "GOODS AND SERVICES TAX")
        c.drawString(160, 755, "REGISTRATION CERTIFICATE")
        c.setFont("Helvetica", 11)
        c.drawString(100, 710, f"GSTIN: {gstin}")
        c.drawString(100, 690, f"Legal Name: {name}")
        c.drawString(100, 670, f"Date of Registration: {reg_date}")
        c.drawString(100, 650, f"Status: {status}")
        c.drawString(100, 620, "This is to certify that the above-named person has been")
        c.drawString(100, 600, "registered under the Goods and Services Tax Act, 2017.")
    _pdf(out / "GST_Certificate.pdf", draw)


def make_expired_gst(out: Path, gstin: str, name: str):
    def draw(c):
        _header(c, "GOODS AND SERVICES TAX")
        c.drawString(160, 755, "REGISTRATION CERTIFICATE")
        c.setFont("Helvetica", 11)
        c.drawString(100, 710, f"GSTIN: {gstin}")
        c.drawString(100, 690, f"Legal Name: {name}")
        c.drawString(100, 670, "Date of Registration: 01-07-2017")
        c.drawString(100, 650, "Valid Until: 31-03-2023")
        c.drawString(100, 630, "Status: Cancelled")
        c.drawString(100, 600, "Note: This registration has been cancelled.")
    _pdf(out / "GST_Certificate.pdf", draw)


def make_emd_and_acceptance(out: Path, name: str, signed=True):
    def draw(c):
        _header(c, "EARNEST MONEY DEPOSIT RECEIPT")
        c.setFont("Helvetica", 11)
        c.drawString(100, 740, f"Received from: {name}")
        c.drawString(100, 720, "Amount: Rs. 10,00,000/- (Ten Lakhs)")
        c.drawString(100, 700, "Mode: Bank Guarantee")
        c.drawString(100, 680, "Against: Construction of Vehicle Parking - CRPF")
        c.drawString(100, 650, "Received by: Contract Cell, CRPF South Zone HQR")
        if signed:
            c.drawString(100, 620, "Authorized Signatory: Sd/-")
        c.showPage()
        _header(c, "TENDER ACCEPTANCE LETTER")
        c.drawString(200, 755, "(Appendix-C)")
        c.setFont("Helvetica", 11)
        c.drawString(100, 720, "To, The Director General, CRPF South Zone HQR, Hyderabad")
        c.drawString(100, 690, "Subject: Tender for Construction of Vehicle Parking")
        c.drawString(100, 660, "We hereby confirm that we have read and understood all")
        c.drawString(100, 640, "terms and conditions of the tender and accept them in full.")
        c.drawString(100, 610, f"For {name}")
        if signed:
            c.drawString(100, 585, "Sd/-")
            c.drawString(100, 565, "Managing Director")
        c.drawString(100, 545, "Date: 15-04-2025")
    _pdf(out / "EMD_and_Acceptance.pdf", draw)


def make_experience_certs(out: Path, name: str, works: list[dict]):
    def draw(c):
        for i, work in enumerate(works):
            if i > 0:
                c.showPage()
            _header(c, "WORK COMPLETION CERTIFICATE")
            c.setFont("Helvetica", 11)
            c.drawString(100, 740, f"This is to certify that M/s {name}")
            c.drawString(100, 720, "has satisfactorily completed the following work:")
            c.drawString(100, 690, f"Name of Work: {work['description']}")
            c.drawString(100, 670, f"Agreement Value: Rs. {work['value']}")
            c.drawString(100, 650, f"Completion Date: {work['date']}")
            c.drawString(100, 630, f"Client: {work['client']}")
            c.drawString(100, 600, "The work was completed to satisfaction.")
            c.drawString(100, 570, "Sd/-")
            c.drawString(100, 550, f"Executive Engineer, {work['client']}")
    _pdf(out / "Experience_Certificates.pdf", draw)


def generate_all():
    base = Path("seed")

    # ── Bidder 1: Arun Builders — ELIGIBLE ────────────────────────────
    out = base / "bidder_arun_builders"
    out.mkdir(parents=True, exist_ok=True)
    make_gst_cert(out, "36AABCA1234M1Z1", "Arun Builders Pvt Ltd")
    make_emd_and_acceptance(out, "Arun Builders Pvt Ltd")
    make_experience_certs(out, "Arun Builders Pvt Ltd", [
        {"description": "Construction of Barracks at BSF Camp", "value": "9,50,00,000/-", "date": "15-06-2023", "client": "CPWD"},
        {"description": "Construction of Vehicle Shed at CRPF Camp", "value": "7,80,00,000/-", "date": "20-12-2022", "client": "MES"},
        {"description": "Construction of Boundary Wall and Guard Room", "value": "5,20,00,000/-", "date": "10-03-2024", "client": "CPWD"},
    ])
    print(f"Created: {out}")

    # ── Bidder 2: Sharma Infrastructure — ELIGIBLE ────────────────────
    out = base / "bidder_sharma_infra"
    out.mkdir(parents=True, exist_ok=True)
    make_gst_cert(out, "29AABCS5678N1Z2", "Sharma Infrastructure Ltd")
    make_emd_and_acceptance(out, "Sharma Infrastructure Ltd")
    make_experience_certs(out, "Sharma Infrastructure Ltd", [
        {"description": "Construction of Residential Quarters at Army Station", "value": "12,00,00,000/-", "date": "01-01-2024", "client": "MES"},
        {"description": "Parking and Road Construction at CISF Campus", "value": "8,00,00,000/-", "date": "15-08-2023", "client": "CPWD"},
    ])
    print(f"Created: {out}")

    # ── Bidder 3: Metro Construction — NOT ELIGIBLE (missing EMD) ─────
    out = base / "bidder_metro_construction"
    out.mkdir(parents=True, exist_ok=True)
    make_gst_cert(out, "27AABCM9012P1Z3", "Metro Construction Co")
    # No EMD/acceptance letter!
    make_experience_certs(out, "Metro Construction Co", [
        {"description": "Building Construction at Police HQ", "value": "6,00,00,000/-", "date": "20-09-2023", "client": "PWD Maharashtra"},
    ])
    print(f"Created: {out} (no EMD)")

    # ── Bidder 4: Lakshmi Enterprises — NOT ELIGIBLE (expired GST) ────
    out = base / "bidder_lakshmi_enterprises"
    out.mkdir(parents=True, exist_ok=True)
    make_expired_gst(out, "36AABCL3456Q1Z4", "Lakshmi Enterprises")
    make_emd_and_acceptance(out, "Lakshmi Enterprises")
    make_experience_certs(out, "Lakshmi Enterprises", [
        {"description": "Road Construction near Military Station", "value": "4,50,00,000/-", "date": "05-05-2023", "client": "BRO"},
    ])
    print(f"Created: {out} (expired GST)")

    # ── Bidder 5: National Projects — NEEDS REVIEW (borderline exp) ───
    out = base / "bidder_national_projects"
    out.mkdir(parents=True, exist_ok=True)
    make_gst_cert(out, "09AABCN7890R1Z5", "National Projects India Ltd")
    make_emd_and_acceptance(out, "National Projects India Ltd")
    # One experience cert with ambiguous description
    make_experience_certs(out, "National Projects India Ltd", [
        {"description": "Supply and Installation of Prefabricated Structures", "value": "11,00,00,000/-", "date": "01-02-2024", "client": "Railways"},
    ])
    print(f"Created: {out} (borderline experience)")

    print("\nAll demo bidder data generated!")


if __name__ == "__main__":
    generate_all()
