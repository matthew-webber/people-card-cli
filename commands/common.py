"""
Common helpers for People Card CLI commands.
"""

from constants import DOMAINS


def display_domains():
    """Display all available domains."""
    for i, domain in enumerate(DOMAINS, 1):
        print(f"  {i}. {domain['full_name']} ({domain['url']})")


def print_help_for_command(command, state):
    if command == "report":
        print("Usage: report [--force] [<domain> <row1> [row2 ...]]")
        print("Generate an HTML report for specified rows or current context.")
    elif command == "bulk_check":
        print("Usage: bulk_check [csv_filename]")
        print("Process multiple pages from a CSV file and update it with link counts.")
    elif command == "extract":
        print("Usage: extract [<domain> <row>]")
        print("Generate or open a people list file for current page or specified page.")
        print("Files are saved to ./people/ directory and used by scan command.")
    elif command == "open":
        print("Usage: open [<target>]")
        print("Open resources in their default applications.")
        print(
            "Targets: (none) - open current URL, dsm - open DSM file, page/url - open current URL, report - open current report"
        )
    elif command == "scan":
        print("Usage: scan")
        print(
            "Scan latest pct-*.xlsx for name matches using names.txt or extracted list."
        )
        print("Generates JavaScript snippet for browser console execution.")
        print("Copy the console output and paste it back into the CLI for processing.")
    elif command == "history":
        print("Usage: history [clear|stats]")
        print("View recent command history, clear history, or show statistics.")
        print("Use up/down arrow keys to navigate through command history.")
    else:
        print(f"No help available for {command}.")


def cmd_help(args, state):
    print("\nPEOPLE CARD CLI - COMMAND REFERENCE")
    print("  report [--force] [<domain> <row1> [row2 ...]]")
    print("  scan              # scan latest pct-*.xlsx and copy/paste data")
    print("  extract [<domain> <row>]  # generate/open people list file for page")
    print("  open [<target>]   # open URL, DSM file, or report in default app")
    print("  bulk_check [csv_filename]")
    print("  history [clear|stats]  # view/manage command history (use ↑/↓ arrows)")
    print("  help [command]")
    print("  exit, quit")
