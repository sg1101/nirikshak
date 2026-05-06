#!/usr/bin/env python3
"""
Nirikshak Demo Data — Bidder Packet Generator

Reads a bidder YAML config + a tender YAML config and produces a complete
multi-document PDF packet for the bidder. Each PDF is a separate file
representing one document the bidder would submit (cover letter, GST
certificate, completion certificates, etc.).

Usage:
    python3 generate_bidder.py --bidder bidder_configs/bidder_01.yaml \\
                               --tender bidder_configs/tender_construction.yaml \\
                               --out output/bidder_01

Then run with --scan-effect to additionally produce scanned-look variants
of selected documents (used for the demo's mixed format requirement).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

GEN_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = GEN_DIR / "templates"
STATIC_DIR = GEN_DIR / "static"

# -----------------------------------------------------------------------------
# Document registry — maps a logical name to a template + output filename
# Order matters; this is the order they appear in a real bidder packet.
# -----------------------------------------------------------------------------

DOCUMENTS = [
    ("01_cover_letter",        "cover_letter.html"),
    ("02_company_profile",     "company_profile.html"),
    ("03_audited_financials",  "audited_financials.html"),
    ("04_ca_turnover_cert",    "ca_turnover_cert.html"),
    ("05_gst_certificate",     "gst_certificate.html"),
    ("06_pan_card",            "pan_card.html"),
    ("07_epf_esi",             "epf_esi.html"),
    ("08_iso_certificate",     "iso_certificate.html"),
    ("09_emd_bank_guarantee",  "emd_bank_guarantee.html"),
    ("10_tender_acceptance",   "tender_acceptance.html"),
    ("11_integrity_pact",      "integrity_pact.html"),
    ("12_cpwd_enlistment",     "cpwd_enlistment.html"),
]

# Completion certificates are emitted one PDF per project.
COMPLETION_CERT_TEMPLATE = "completion_certificate.html"


# -----------------------------------------------------------------------------
# Number / currency formatting helpers (Indian numbering system)
# -----------------------------------------------------------------------------

def format_inr(amount: int | float) -> str:
    """Format a rupee amount in Indian numbering: 12,34,56,789.00"""
    amount = float(amount)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    integer_part = int(amount)
    fractional = round(amount - integer_part, 2)
    s = str(integer_part)
    if len(s) <= 3:
        formatted = s
    else:
        last_three = s[-3:]
        rest = s[:-3]
        # Group rest in pairs from right
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        formatted = ",".join(reversed(groups)) + "," + last_three
    if fractional > 0:
        cents = int(round(fractional * 100))
        return f"{sign}{formatted}.{cents:02d}"
    return f"{sign}{formatted}.00"


def number_to_indian_words(amount: int | float) -> str:
    """Convert a number to Indian English words, e.g. 50000000 -> Five Crore."""
    amount = int(round(float(amount)))
    if amount == 0:
        return "Zero"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
             "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
             "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two_digits(n):
        if n < 20:
            return units[n]
        return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")

    def three_digits(n):
        if n < 100:
            return two_digits(n)
        return units[n // 100] + " Hundred" + (" " + two_digits(n % 100) if n % 100 else "")

    crore = amount // 10000000
    amount %= 10000000
    lakh = amount // 100000
    amount %= 100000
    thousand = amount // 1000
    amount %= 1000
    hundred = amount

    parts = []
    if crore:
        parts.append(three_digits(crore) + " Crore")
    if lakh:
        parts.append(two_digits(lakh) + " Lakh")
    if thousand:
        parts.append(two_digits(thousand) + " Thousand")
    if hundred:
        parts.append(three_digits(hundred))

    result = " ".join(parts).strip()
    return f"Rupees {result}"


# -----------------------------------------------------------------------------
# Computed-field helpers
# -----------------------------------------------------------------------------

def enrich_financials(financials: dict) -> dict:
    """Compute formatted strings for turnover history."""
    enriched = dict(financials or {})
    history = enriched.get("turnover_history", []) or []
    enriched_history = []
    total = 0
    for entry in history:
        amount = entry.get("amount", 0)
        total += amount
        enriched_history.append({
            **entry,
            "amount_formatted": format_inr(amount),
            "amount_words": number_to_indian_words(amount),
        })
    enriched["turnover_history"] = enriched_history
    if history:
        avg = total / len(history)
        enriched["turnover_avg_formatted"] = format_inr(avg)
        enriched["turnover_avg_words"] = number_to_indian_words(avg)
    networth = enriched.get("networth", 0)
    if networth:
        enriched["networth_formatted"] = format_inr(networth)
        enriched["networth_words"] = number_to_indian_words(networth)
    return enriched


def enrich_completion_project(project: dict) -> dict:
    """Compute formatted strings for one completion certificate's project."""
    enriched = dict(project)
    if "contract_value" in enriched:
        enriched["contract_value_formatted"] = format_inr(enriched["contract_value"])
        enriched["contract_value_words"] = number_to_indian_words(enriched["contract_value"])
    if "executed_value" in enriched:
        enriched["executed_value_formatted"] = format_inr(enriched["executed_value"])
        enriched["executed_value_words"] = number_to_indian_words(enriched["executed_value"])
    return enriched


def enrich_tender(tender: dict) -> dict:
    """Compute formatted strings on the tender side."""
    enriched = dict(tender)
    emd = enriched.get("emd_amount", 0)
    if emd:
        enriched["emd_amount_formatted"] = format_inr(emd)
        enriched["emd_amount_words"] = number_to_indian_words(emd)
        enriched["emd_amount_text"] = number_to_indian_words(emd).replace("Rupees ", "")
    return enriched


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------

def make_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html(env: Environment, template_name: str, context: dict, dest: Path) -> Path:
    """Render an HTML template with context to dest. Returns the dest path."""
    template = env.get_template(template_name)
    html = template.render(**context)
    dest.write_text(html, encoding="utf-8")
    return dest


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    """Convert HTML file to PDF using wkhtmltopdf."""
    cmd = [
        "wkhtmltopdf",
        "--quiet",
        "--enable-local-file-access",
        "--encoding", "utf-8",
        "--page-size", "A4",
        "--margin-top", "12mm",
        "--margin-bottom", "12mm",
        "--margin-left", "14mm",
        "--margin-right", "14mm",
        str(html_path),
        str(pdf_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_one_document(env: Environment, template_name: str, context: dict,
                        out_dir: Path, basename: str) -> Path:
    """Render a single document: HTML to a temp dir, then PDF into out_dir."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # Copy static dir so CSS resolves
        shutil.copytree(STATIC_DIR, td_path / "static")
        html_path = td_path / f"{basename}.html"
        render_html(env, template_name, context, html_path)
        pdf_path = out_dir / f"{basename}.pdf"
        html_to_pdf(html_path, pdf_path)
        return pdf_path


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def build_packet(bidder_cfg_path: Path, tender_cfg_path: Path, out_dir: Path) -> None:
    bidder = yaml.safe_load(bidder_cfg_path.read_text(encoding="utf-8"))
    tender = enrich_tender(yaml.safe_load(tender_cfg_path.read_text(encoding="utf-8")))

    # Computed fields shared across templates
    submission_year = bidder.get("submission_year", 2025)
    submission_date_long = bidder.get("submission_date_long", "15 May 2025")
    fy_minus_1 = bidder.get("fy_minus_1", "2024-25")
    fy_minus_2 = bidder.get("fy_minus_2", "2023-24")
    fy_minus_3 = bidder.get("fy_minus_3", "2022-23")

    financials = enrich_financials(bidder.get("financials", {}))

    base_context = {
        "bidder": bidder,
        "tender": tender,
        "ca": bidder.get("ca", {}),
        "iso": bidder.get("iso", {}),
        "cpwd": bidder.get("cpwd_authority", {}),
        "gst_officer": bidder.get("gst_officer", {}),
        "financials": financials,
        "submission_year": submission_year,
        "submission_date_long": submission_date_long,
        "fy_minus_1": fy_minus_1,
        "fy_minus_2": fy_minus_2,
        "fy_minus_3": fy_minus_3,
    }

    out_dir.mkdir(parents=True, exist_ok=True)

    env = make_jinja_env()

    # --- Render all single-instance documents ---
    for basename, template in DOCUMENTS:
        try:
            pdf_path = render_one_document(env, template, base_context, out_dir, basename)
            print(f"  ✓ {pdf_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ {basename}: {e.stderr.decode('utf-8', errors='replace')[:200]}", file=sys.stderr)

    # --- Render completion certificates (one per project) ---
    projects = bidder.get("completion_projects", [])
    for idx, project in enumerate(projects, start=1):
        enriched = enrich_completion_project(project)
        ctx = dict(base_context, project=enriched)
        basename = f"13_completion_cert_{idx:02d}"
        try:
            pdf_path = render_one_document(env, COMPLETION_CERT_TEMPLATE, ctx, out_dir, basename)
            print(f"  ✓ {pdf_path.name}  ({project.get('short_name', '')})")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ {basename}: {e.stderr.decode('utf-8', errors='replace')[:200]}", file=sys.stderr)


def parse_args():
    p = argparse.ArgumentParser(description="Generate a bidder document packet.")
    p.add_argument("--bidder", required=True, help="Path to bidder YAML config")
    p.add_argument("--tender", required=True, help="Path to tender YAML config")
    p.add_argument("--out", required=True, help="Output directory")
    return p.parse_args()


def main():
    args = parse_args()
    bidder_path = Path(args.bidder).resolve()
    tender_path = Path(args.tender).resolve()
    out_dir = Path(args.out).resolve()

    if not bidder_path.exists():
        sys.exit(f"Bidder config not found: {bidder_path}")
    if not tender_path.exists():
        sys.exit(f"Tender config not found: {tender_path}")

    print(f"Building packet for {bidder_path.name} → {out_dir}")
    build_packet(bidder_path, tender_path, out_dir)
    print(f"Done.")


if __name__ == "__main__":
    main()
