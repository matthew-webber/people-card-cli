"""
Person command - Search for people by name in Excel reports.

This command accepts 1 or more people names (separated by |) and searches
the Excel files in people_reports directory for matching entries in the
'Full Name' and 'Headshot String' columns.
"""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from utils.people_names import get_name_before_comma, key_variants_from_name


def parse_names(names_input: str) -> List[str]:
    """Parse names from input string, splitting on | and removing credentials."""
    raw_names = [name.strip() for name in names_input.split("|") if name.strip()]
    processed_names = []

    for raw_name in raw_names:
        # Remove credentials using the utility function
        clean_name = get_name_before_comma(raw_name)
        if clean_name:
            processed_names.append(clean_name)

    return processed_names


def search_excel_files(names: List[str]) -> Dict[str, Dict]:
    """
    Search Excel files in people_reports for matching names.

    Returns dict with name as key and dict containing:
    - found: bool
    - full_name: str (if found)
    - headshot_string: str (if found)
    - file_source: str (if found)
    """
    results = {}
    reports_dir = Path("people_reports")

    if not reports_dir.exists():
        print(f"❌ Reports directory not found: {reports_dir}")
        return results

    # Initialize results for all names
    for name in names:
        results[name] = {
            "found": False,
            "full_name": None,
            "headshot_string": None,
            "file_source": None,
        }

    # Get all Excel files in the reports directory
    excel_files = list(reports_dir.glob("*.xlsx"))
    excel_files = [
        f for f in excel_files if not f.name.startswith("~$")
    ]  # Skip temp files

    if not excel_files:
        print(f"❌ No Excel files found in {reports_dir}")
        return results

    # Search each Excel file
    for excel_file in excel_files:
        try:
            df = pd.read_excel(excel_file, engine="openpyxl")

            # Look for 'Full Name' and 'Headshot String' columns
            full_name_col = None
            headshot_col = None

            for col in df.columns:
                if str(col).lower().strip() == "full name":
                    full_name_col = col
                elif str(col).lower().strip() == "headshot string":
                    headshot_col = col

            if full_name_col is None:
                print(f"⚠️  No 'Full Name' column found in {excel_file.name}")
                continue
            else:
                # Search for each name
                for search_name in names:
                    if results[search_name]["found"]:
                        continue  # Already found this name

                    # Generate key variants for matching
                    search_variants = key_variants_from_name(search_name)

                    # Search through the Full Name column
                    for idx in df.index:
                        row_name = df.loc[idx, full_name_col]
                        if pd.isna(row_name):
                            continue

                        row_name_str = str(row_name).strip()
                        if not row_name_str:
                            continue

                        # Generate variants for the row name
                        row_variants = key_variants_from_name(row_name_str)

                        # Check if any search variant matches any row variant
                        if any(sv in row_variants for sv in search_variants):
                            headshot_value = None
                            if headshot_col is not None:
                                headshot_raw = df.loc[idx, headshot_col]
                                if not pd.isna(headshot_raw):
                                    headshot_value = str(headshot_raw)

                            results[search_name] = {
                                "found": True,
                                "full_name": row_name_str,
                                "headshot_string": headshot_value,
                                "file_source": excel_file.name,
                            }
                            break

        except Exception as e:
            print(f"❌ Error reading {excel_file.name}: {e}")
            continue

    return results


def print_results_table(results: Dict[str, Dict]) -> None:
    """Print results in a tabular format."""
    if not results:
        print("❌ No results to display")
        return

    print("\n📋 PERSON SEARCH RESULTS")
    print("=" * 80)

    # Calculate column widths
    max_name_width = max(len(name) for name in results.keys())
    max_name_width = max(max_name_width, len("Name"))

    max_status_width = len("Status")
    max_source_width = max(
        len(result.get("file_source", ""))
        for result in results.values()
        if result.get("file_source")
    )
    max_source_width = (
        max(max_source_width, len("Source")) if max_source_width else len("Source")
    )

    # Header
    print(
        f"{'Name':<{max_name_width}} | {'Status':<{max_status_width}} | {'Source':<{max_source_width}} | Headshot"
    )
    print("-" * (max_name_width + max_status_width + max_source_width + 50))

    # Results
    for name, result in results.items():
        if result["found"]:
            status = "✅ Found"
            source = result["file_source"] or "Unknown"
            headshot_status = (
                "❌ None"
                if not result["headshot_string"]
                else (
                    "⚠️  Placeholder"
                    if "placeholder" in result["headshot_string"].lower()
                    else "✅ Yes"
                )
            )
        else:
            status = "❌ Not Found"
            source = "-"
            headshot_status = "-"

        print(
            f"{name:<{max_name_width}} | {status:<{max_status_width}} | {source:<{max_source_width}} | {headshot_status}"
        )

    print()


def categorize_results(
    names: List[str], results: Dict[str, Dict]
) -> Dict[str, List[str]]:
    """Categorize results into different lists for return value."""
    categorized = {
        "names_processed": names.copy(),
        "names_not_found": [],
        "names_found_no_headshot": [],
        "names_found_placeholder_headshot": [],
    }

    for name, result in results.items():
        if not result["found"]:
            categorized["names_not_found"].append(name)
        elif not result["headshot_string"]:
            categorized["names_found_no_headshot"].append(name)
        elif "placeholder" in result["headshot_string"].lower():
            categorized["names_found_placeholder_headshot"].append(name)

    return categorized


def cmd_person(args, state):
    """
    Person command handler.

    Usage: person <name1> [| <name2> | <name3> ...]
    Searches Excel files for people by name.
    """
    if not args:
        print("❌ No names provided")
        print("Usage: person <name1> [| <name2> | <name3> ...]")
        print("Example: person John Smith | Jane Doe, MD | Robert Johnson")
        return {}

    # Join all args and parse names
    names_input = " ".join(args)
    names = parse_names(names_input)

    if not names:
        print("❌ No valid names found after processing")
        return {}

    print(f"🔍 Searching for {len(names)} name(s)...")

    # Search Excel files
    results = search_excel_files(names)

    # Print results table
    print_results_table(results)

    # Categorize and return results
    categorized = categorize_results(names, results)

    # Print summary
    found_count = len([r for r in results.values() if r["found"]])
    print(f"📊 Summary: {found_count}/{len(names)} names found")
    if categorized["names_not_found"]:
        print(f"   ❌ Not found: {len(categorized['names_not_found'])}")
    if categorized["names_found_no_headshot"]:
        print(f"   ⚠️  No headshot: {len(categorized['names_found_no_headshot'])}")
    if categorized["names_found_placeholder_headshot"]:
        print(
            f"   ⚠️  Placeholder headshot: {len(categorized['names_found_placeholder_headshot'])}"
        )

    return categorized
