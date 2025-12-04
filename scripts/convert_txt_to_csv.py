"""
Convert TXT file with Spanish addresses to CSV format.
"""

import csv
from pathlib import Path


def convert_txt_to_csv(txt_path: Path, csv_path: Path) -> None:
    """Convert address TXT file to proper CSV format."""
    records = []

    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Skip header line
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Split by comma, but be careful: address and notes may contain commas
        # Format: address,city,zip,notes
        # Strategy: split and take first part as address, then city, zip, rest as notes
        parts = line.split(",")

        if len(parts) >= 3:
            # Find the zip code (should be 5 digits) to properly split
            # Work backwards from parts to find zip code
            zip_idx = None
            for i, part in enumerate(parts):
                if part.strip().isdigit() and len(part.strip()) == 5:
                    zip_idx = i
                    break

            if zip_idx and zip_idx >= 2:
                address = ",".join(parts[:zip_idx - 1]).strip()
                city = parts[zip_idx - 1].strip()
                zip_code = parts[zip_idx].strip()
                notes = ",".join(parts[zip_idx + 1:]).strip() if len(parts) > zip_idx + 1 else ""

                records.append({
                    "address": address,
                    "city": city,
                    "zip": zip_code,
                    "notes": notes
                })

    # Save to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["address", "city", "zip", "notes"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Converted {len(records)} records from {txt_path} to {csv_path}")


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    txt_path = project_root / "data" / "raw" / "addresses.txt"
    csv_path = project_root / "data" / "processed" / "addresses.csv"

    print(f"Reading from: {txt_path}")
    convert_txt_to_csv(txt_path, csv_path)


if __name__ == "__main__":
    main()
