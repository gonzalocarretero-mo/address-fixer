#!/usr/bin/env python3
"""
Process addresses through the validation pipeline.

Usage:
    uv run python scripts/process_addresses.py [--no-llm] [--limit N]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import AddressPipeline


def main():
    parser = argparse.ArgumentParser(description="Process addresses through validation pipeline")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/addresses.csv"),
        help="Input CSV file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/validated_addresses.csv"),
        help="Output CSV file",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM for faster processing (less accurate)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of rows to process",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    reference_dir = project_root / "data" / "reference" / "postal-codes"

    # Convert relative paths to absolute
    input_path = args.input if args.input.is_absolute() else project_root / args.input
    output_path = args.output if args.output.is_absolute() else project_root / args.output

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"LLM enabled: {not args.no_llm}")
    if args.limit:
        print(f"Limit: {args.limit} rows")

    # Initialize pipeline
    print("\nInitializing pipeline...")
    pipeline = AddressPipeline(
        reference_dir=reference_dir,
        use_llm=not args.no_llm,
    )

    # Process addresses
    print("\nProcessing addresses...")
    stats = pipeline.process_csv(
        input_path=input_path,
        output_path=output_path,
        address_col="address",
        city_col="city",
        postcode_col="zip",
        limit=args.limit,
    )

    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total processed: {stats['total']}")
    print(f"  Valid: {stats['valid']}")
    print(f"  Valid (normalized): {stats['valid_normalized']}")
    print(f"  Invalid (format): {stats['invalid_format']}")
    print(f"  Invalid (mismatch): {stats['invalid_mismatch']}")
    print(f"  Nonsense: {stats['nonsense']}")
    print(f"  Needs review: {stats['needs_review']}")
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
