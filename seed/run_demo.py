"""One-click demo setup: upload tender + all bidders. Run from project root."""

import sys
import time
from pathlib import Path

import httpx

API = "http://localhost:8000"
TIMEOUT = 300


def check_api():
    try:
        r = httpx.get(f"{API}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def upload_tender():
    tender_pdf = Path("seed") / "test_bidder_1" / ".." / ".." / "documents"
    # Use the sample tender if available, otherwise skip
    candidates = [
        Path("/Users/shubham/Downloads/sample_tender.pdf"),
        Path("documents/sample_tender.pdf"),
    ]
    tender_path = None
    for c in candidates:
        if c.exists():
            tender_path = c
            break

    if not tender_path:
        print("No sample tender PDF found. Please place it at /Users/shubham/Downloads/sample_tender.pdf")
        sys.exit(1)

    print(f"Uploading tender: {tender_path.name}...")
    r = httpx.post(
        f"{API}/api/tenders/upload",
        data={
            "title": "Construction of Vehicle Parking - CRPF Zone Bangalore",
            "procuring_authority": "CRPF Zone Bangalore",
            "bid_submission_date": "2025-04-30",
            "estimated_value": "500000000",
        },
        files={"file": (tender_path.name, tender_path.read_bytes(), "application/pdf")},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    result = r.json()
    tender_id = result["tender_id"]
    spec = result.get("criteria_spec")
    criteria_count = len(spec["criteria"]) if spec else 0
    print(f"  Tender uploaded: {tender_id}")
    print(f"  Criteria extracted: {criteria_count}")

    # Inject FIN-001 + QUA-001 (not always extracted by LLM from tender PDF)
    if spec:
        r = httpx.post(
            f"{API}/api/criteria-specs/{spec['id']}/add-criteria",
            timeout=30,
        )
        r.raise_for_status()
        added = r.json().get("added_criteria", [])
        if added:
            print(f"  Injected seed criteria: {added}")
        criteria_count += len(added)
        print(f"  Total criteria: {criteria_count}")

    # Lock the spec
    if spec:
        r = httpx.post(
            f"{API}/api/criteria-specs/{spec['id']}/lock",
            data={"officer_email": "officer1@crpf.gov.in"},
            timeout=30,
        )
        r.raise_for_status()
        print(f"  Criteria spec locked")

    return tender_id


def upload_bidder(tender_id: str, bidder_dir: Path, bidder_name: str):
    files_to_upload = [f for f in sorted(bidder_dir.iterdir()) if f.is_file() and not f.name.startswith(".")]
    if not files_to_upload:
        print(f"  Skipping {bidder_name}: no files in {bidder_dir}")
        return

    print(f"  Uploading {bidder_name} ({len(files_to_upload)} files)...")
    files = [("files", (f.name, f.read_bytes(), "application/pdf")) for f in files_to_upload]

    r = httpx.post(
        f"{API}/api/tenders/{tender_id}/bidders/upload",
        data={"bidder_name": bidder_name},
        files=files,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    result = r.json()
    verdict = result["aggregate_verdict"]
    emoji = {"eligible": "✅", "not_eligible": "❌", "needs_review": "⚠️"}.get(verdict, "❓")
    print(f"    → {emoji} {verdict.upper()}")
    for pc in result["per_criterion"]:
        e = {"eligible": "✅", "not_eligible": "❌", "needs_review": "⚠️"}.get(pc["state"], "❓")
        print(f"      {pc['criterion_id']}: {e} {pc['state']} — {pc['reason'][:60]}")


def main():
    if not check_api():
        print("API not running. Start it with: uvicorn nirikshak.api.main:app --port 8000")
        sys.exit(1)

    # Generate demo data
    print("=" * 60)
    print("NIRIKSHAK DEMO SETUP")
    print("=" * 60)

    print("\n1. Generating mock bidder documents...")
    from seed.generate_demo_data import generate_all
    generate_all()

    print("\n2. Uploading tender...")
    tender_id = upload_tender()

    print("\n3. Uploading bidders...")
    bidder_dirs = {
        "bidder_arun_builders": "Arun Builders Pvt Ltd",
        "bidder_sharma_infra": "Sharma Infrastructure Ltd",
        "bidder_metro_construction": "Metro Construction Co",
        "bidder_lakshmi_enterprises": "Lakshmi Enterprises",
        "bidder_national_projects": "National Projects India Ltd",
    }

    for dirname, name in bidder_dirs.items():
        bidder_path = Path("seed") / dirname
        if bidder_path.exists():
            upload_bidder(tender_id, bidder_path, name)
            time.sleep(1)  # small pause between bidders
        else:
            print(f"  Skipping {name}: directory {bidder_path} not found")

    # Verify audit chain
    print("\n4. Verifying audit chain...")
    r = httpx.get(f"{API}/api/audit/verify", timeout=10)
    result = r.json()
    if result["valid"]:
        print("  ✅ Audit chain valid")
    else:
        print(f"  ❌ Chain broken at sequence {result['broken_at_sequence']}")

    print("\n" + "=" * 60)
    print("Demo setup complete!")
    print(f"Open Streamlit console: http://localhost:8501")
    print(f"API docs: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
