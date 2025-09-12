#!/usr/bin/env python3
"""
Legacy entrypoint for the PCT scanner.

This script has been integrated into the main CLI as the 'scan' command.
You can now run it inside the People Card CLI:

  $ python main.py
  people_card_user > scan

This shim simply invokes the new command implementation.
"""

from commands.scan import cmd_scan


if __name__ == "__main__":
    cmd_scan([])

