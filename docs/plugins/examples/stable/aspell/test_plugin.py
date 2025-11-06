#!/usr/bin/env python3
"""
Test script for the Aspell spell check plugin
"""

import sys
import os

# Add the plugin directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

import aspell

def test_plugin():
    """Test the aspell plugin functionality."""
    print("=== Aspell Plugin Test ===\\n")
    
    # Test 1: Single misspelled word
    print("Test 1: Single misspelled word")
    text1 = "This is a mispelled word"
    errors1 = aspell._check_spelling(text1)
    print(f"Input: {text1}")
    print(f"Errors found: {errors1}")
    aspell._display_spell_errors(errors1)
    print()
    
    # Test 2: Multiple misspelled words
    print("Test 2: Multiple misspelled words")
    text2 = "There are mispelled words in this sentance and anothr one"
    errors2 = aspell._check_spelling(text2)
    print(f"Input: {text2}")
    print(f"Errors found: {errors2}")
    aspell._display_spell_errors(errors2)
    print()
    
    # Test 3: Correctly spelled text
    print("Test 3: Correctly spelled text")
    text3 = "This is correctly spelled text with no errors"
    errors3 = aspell._check_spelling(text3)
    print(f"Input: {text3}")
    print(f"Errors found: {errors3}")
    aspell._display_spell_errors(errors3)
    print()
    
    # Test 4: Empty text
    print("Test 4: Empty text")
    text4 = ""
    errors4 = aspell._check_spelling(text4)
    print(f"Input: (empty)")
    print(f"Errors found: {errors4}")
    aspell._display_spell_errors(errors4)
    print()
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_plugin()