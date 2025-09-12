#!/usr/bin/env python3
"""
Test the delimited data parsing functionality.
"""

# Sample delimited data that would come from JavaScript
test_data = [
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
        print("Input data:")
        for i, line in enumerate(test_data, 1):
            print(f"  {i}: {line}")

        print("\nParsing...")
        _process_pasted_data(test_data)

        print("✅ Test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_parse()
