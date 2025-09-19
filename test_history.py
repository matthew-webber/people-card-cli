#!/usr/bin/env python3
"""
Test script to verify the history functionality works correctly.
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, "/Users/m/dev/migration/people-card-cli")

from utils.history import CommandHistory


def test_history_basic():
    """Test basic history functionality."""
    print("🧪 Testing basic history functionality...")

    # Use a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".history") as f:
        temp_history_file = f.name

    try:
        # Create history instance with temp file
        history = CommandHistory(temp_history_file)

        # Test adding commands
        test_commands = ["help", "show vars", "scan", "help history", "history stats"]

        for cmd in test_commands:
            history.add_command(cmd)

        # Save history
        history.save_history()

        # Verify file was created
        assert os.path.exists(temp_history_file), "History file should exist"

        # Read the file contents
        with open(temp_history_file, "r") as f:
            saved_commands = [line.strip() for line in f.readlines() if line.strip()]

        print(f"✅ Saved {len(saved_commands)} commands to history file")
        for i, cmd in enumerate(saved_commands, 1):
            print(f"  {i}: {cmd}")

        # Test loading history in a new instance
        new_history = CommandHistory(temp_history_file)
        stats = new_history.get_history_stats()

        print(f"✅ History stats: {stats}")

        print("✅ Basic history functionality test passed!")

    finally:
        # Clean up
        if os.path.exists(temp_history_file):
            os.unlink(temp_history_file)


def test_duplicate_prevention():
    """Test that duplicate consecutive commands are prevented."""
    print("\n🧪 Testing duplicate command prevention...")

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".history") as f:
        temp_history_file = f.name

    try:
        history = CommandHistory(temp_history_file)

        # Add same command multiple times
        history.add_command("help")
        history.add_command("help")  # Should be ignored
        history.add_command("help")  # Should be ignored
        history.add_command("scan")  # Should be added
        history.add_command("scan")  # Should be ignored

        history.save_history()

        with open(temp_history_file, "r") as f:
            saved_commands = [line.strip() for line in f.readlines() if line.strip()]

        expected = ["help", "scan"]
        assert saved_commands == expected, f"Expected {expected}, got {saved_commands}"

        print("✅ Duplicate prevention test passed!")

    finally:
        if os.path.exists(temp_history_file):
            os.unlink(temp_history_file)


if __name__ == "__main__":
    test_history_basic()
    test_duplicate_prevention()
    print("\n🎉 All history tests passed!")
