"""
Extract command for generating people list files.

This command generates a text file for the currently loaded page where users can
paste names of people found on the page. It acts as a companion to the scan command.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from commands.common import print_help_for_command
from utils.core import debug_print


def cmd_extract(args, state):
    """Generate or open an extracted people list file for the current page."""

    # If arguments are provided, use them to set domain and row like the report command
    if args:
        first_row_idx = next((i for i, a in enumerate(args) if a.isdigit()), None)
        if first_row_idx is None:
            return print_help_for_command("extract", state)

        domain = " ".join(args[:first_row_idx])
        row = args[first_row_idx]

        # Load the specified page
        from commands.load import cmd_load

        cmd_load([domain, row], state)

    # Get current domain and row from state
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")

    if not domain or not row:
        print(
            "❌ No page loaded. Please load a page first with 'load <domain> <row>' or provide arguments."
        )
        return

    # Create people directory if it doesn't exist
    people_dir = Path("./people")
    people_dir.mkdir(exist_ok=True)

    # Generate filename based on domain and row (similar to report generation)
    clean_domain = re.sub(r"[^a-zA-Z0-9]", "_", domain.lower())
    filename = f"./people/{clean_domain}_{row}_people.txt"

    file_path = Path(filename)

    if file_path.exists():
        print(f"📄 People list file already exists: {filename}")
        print("🔄 Opening existing file...")
    else:
        print(f"📝 Creating new people list file: {filename}")

        # Create the file with helpful instructions
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# People list for {domain} {row}\n")
            f.write(f"# Paste the names of people found on this page below.\n")
            f.write(f"# One name per line.\n")
            f.write(f"# Lines starting with # are ignored.\n")
            f.write(f"#\n")
            f.write(f"# Page: {state.get_variable('URL')}\n")
            f.write(f"#\n")
            f.write(f"\n")

        print(f"✅ Created: {filename}")

    # Update the state with the extracted people list filename
    state.set_variable("EXTRACTED_PEOPLE_LIST", filename)

    # Open the file in the default text editor
    try:
        _open_file_in_editor(filename)
        print(f"📂 Opened {filename} in default editor")
    except Exception as e:
        print(f"⚠️  Could not open file automatically: {e}")
        print(f"📍 Please open manually: {filename}")

    # Chain the open command to open the URL in browser
    from commands.core import cmd_open

    cmd_open(["existing_urls"], state)


def _open_file_in_editor(filepath):
    """Open a file in the default text editor."""
    if sys.platform == "darwin":  # macOS
        subprocess.run(["open", filepath], check=True)
    elif sys.platform == "win32":  # Windows
        os.startfile(filepath)
    else:  # Linux and others
        subprocess.run(["xdg-open", filepath], check=True)
