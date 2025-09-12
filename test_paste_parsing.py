#!/usr/bin/env python3
"""
Test the delimited data parsing functionality.
"""

# Sample delimited data that would come from JavaScript (reproducing the user's issue)
test_data_with_newlines = [
    "Terri;Barnes;true;Headshots/B/barnes-terri_SC;\\nJames;Battle;true;Headshots/B/battle-james_SC;\\nHenry;Butehorn;true;Headshots/B/butehorn-henry_SC;\\nRichard;Christian;true;Headshots/C/christian-richard_SC;\\nPaul;Davis;true;Headshots/D/davis-paul_SC;"
]

# Sample delimited data with proper separate lines
test_data_separate_lines = [
    "John;Doe;true;media/images/john-doe.jpg;john-doe-1234",
    "Jane;Smith;false;;;",
    "Bob;Johnson;true;;bob-johnson-5678",
]


def test_parse():
    """Test parsing the delimited format."""

    # Import the parsing function
    try:
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from commands.scan import _process_pasted_data

        print("🧪 Testing delimited data parsing...")
        print("\n" + "=" * 60)
        print("TEST 1: Data with literal \\n separators (reproducing the issue)")
        print("=" * 60)
        print("Input data:")
        for i, line in enumerate(test_data_with_newlines, 1):
            print(f"  {i}: {line}")

        print("\nParsing...")
        _process_pasted_data(test_data_with_newlines)

        print("\n" + "=" * 60)
        print("TEST 2: Data with proper separate lines")
        print("=" * 60)
        print("Input data:")
        for i, line in enumerate(test_data_separate_lines, 1):
            print(f"  {i}: {line}")

        print("\nParsing...")
        _process_pasted_data(test_data_separate_lines)

        print("✅ All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_parse()
