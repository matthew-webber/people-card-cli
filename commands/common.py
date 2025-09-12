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
    else:
        print(f"No help available for {command}.")


def cmd_help(args, state):
    print("\nPEOPLE CARD CLI - COMMAND REFERENCE")
    print("  report [--force] [<domain> <row1> [row2 ...]]")
    print(
        "  scan              # scan latest pct-*.xlsx using names.txt or extracted list"
    )
    print("  extract [<domain> <row>]  # generate/open people list file for page")
    print("  bulk_check [csv_filename]")
    print("  help [command]")
    print("  exit, quit")
