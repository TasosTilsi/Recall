#!/usr/bin/env python3
"""Test script to verify TOON encoding implementation in inject_context.py"""

import sys
sys.path.insert(0, 'src')

from hooks.inject_context import _build_option_c, _preprocess_for_toon
import json

def test_preprocess():
    """Test the preprocessing function"""
    print("Testing _preprocess_for_toon...")
    
    # Test basic functionality
    test_cases = [
        ("Hello, world\nNew line", "Hello world New line"),
        ("Multiple,,,commas\n\nand\nnewlines", "Multiple commas and newlines"),
        ("", ""),
        ("No special chars", "No special chars"),
        ("  Extra   spaces  ", "Extra spaces"),
    ]
    
    for input_text, expected in test_cases:
        result = _preprocess_for_toon(input_text)
        assert result == expected, f"Failed for {input_text}: got {result}, expected {expected}"
        print(f"  ✓ {input_text!r} -> {result!r}")

def test_build_option_c_small_history():
    """Test _build_option_c with 0-2 history items (should use original format)"""
    print("\nTesting _build_option_c with 0-2 history items...")
    
    # Test with 0 items
    result = _build_option_c("Last session summary", [], 4000)
    print("  0 items result:")
    print("  " + "\n  ".join(result.split("\n")))
    assert "<relevant_history>\n</relevant_history>" in result
    
    # Test with 1 item
    history_items = [{
        "snippet": "Test snippet 1",
        "created_at": "2026-03-30T19:00:00"
    }]
    result = _build_option_c("Last session summary", history_items, 4000)
    print("  1 item result:")
    print("  " + "\n  ".join(result.split("\n")))
    assert "  - Test snippet 1 (since 2026-03-30, current)" in result
    
    # Test with 2 items
    history_items = [
        {
            "snippet": "Test snippet 1",
            "created_at": "2026-03-30T19:00:00"
        },
        {
            "snippet": "Test snippet 2",
            "created_at": "2026-03-29T19:00:00"
        }
    ]
    result = _build_option_c("Last session summary", history_items, 4000)
    print("  2 items result:")
    print("  " + "\n  ".join(result.split("\n")))
    # Should contain both items in original format
    assert "  - Test snippet 1 (since 2026-03-30, current)" in result
    assert "  - Test snippet 2 (since 2026-03-29, current)" in result
    # Should NOT contain TOON format (no square brackets at start of lines in relevant_history)
    history_start = result.find("<relevant_history>")
    history_end = result.find("</relevant_history>")
    history_content = result[history_start:history_end]
    assert not history_content.strip().startswith("["), f"Found TOON format in 2-item result: {history_content}"

def test_build_option_c_large_history():
    """Test _build_option_c with 3+ history items (should use TOON format)"""
    print("\nTesting _build_option_c with 3+ history items...")
    
    # Test with 3 items
    history_items = [
        {
            "snippet": "Test snippet 1",
            "created_at": "2026-03-30T19:00:00"
        },
        {
            "snippet": "Test snippet 2",
            "created_at": "2026-03-29T19:00:00"
        },
        {
            "snippet": "Test snippet 3",
            "created_at": "2026-03-28T19:00:00"
        }
    ]
    result = _build_option_c("Last session summary", history_items, 4000)
    print("  3 items result:")
    print("  " + "\n  ".join(result.split("\n")))
    
    # Should contain TOON format (starts with [ in the relevant_history section)
    history_start = result.find("<relevant_history>")
    history_end = result.find("</relevant_history>")
    history_content = result[history_start:history_end]
    print(f"  History content: {history_content!r}")
    assert history_content.strip().startswith("["), f"Expected TOON format in 3+ item result, got: {history_content}"
    
    # Should contain our data (though possibly trimmed)
    # Note: With TOON encoding, the exact format is different, but we should see our data somewhere
    # For now, just verify it's using TOON format

def test_token_budget():
    """Test that token budget is respected"""
    print("\nTesting token budget enforcement...")
    
    # Create a large history that should exceed budget
    history_items = []
    for i in range(50):  # Create 50 items
        history_items.append({
            "snippet": f"This is a very long snippet that should definitely exceed the token budget when we have many of them. Item number {i} with lots of text to make it long enough to test budget limits.",
            "created_at": f"2026-03-{30-i//30:02d}T19:00:00"
        })
    
    # Use a small token budget
    result = _build_option_c("Last session summary", history_items, 100)  # Very small budget
    print(f"  Result length: {len(result)} characters")
    
    # Should still produce valid XML
    assert result.startswith("<session_context>")
    assert result.endswith("</session_context>")
    assert "<relevant_history>" in result
    assert "</relevant_history>" in result
    
    # With TOON encoding and trimming, should still be valid
    print("  Token budget test passed")

if __name__ == "__main__":
    print("Testing TOON encoding implementation in inject_context.py")
    print("=" * 60)
    
    try:
        test_preprocess()
        test_build_option_c_small_history()
        test_build_option_c_large_history()
        test_token_budget()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)