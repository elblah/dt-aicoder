#!/usr/bin/env python3
"""
Test script for Smart Edit Tool Plugin
"""

import os
import sys
import tempfile

# Add the plugin directory to Python path
sys.path.insert(0, '.')

# Import the plugin
from smart_edit import (
    smart_edit_handler, 
    validate_smart_edit,
    DiffVisualizer,
    BackupManager,
    EditStrategyManager
)

def test_validation():
    """Test the validation function."""
    print("🧪 Testing validation function...")
    
    # Test valid arguments
    valid_args = {
        "file_path": "/tmp/test.txt",
        "changes": [{
            "context": ["old line"],
            "replacement": ["new line"]
        }]
    }
    
    result = validate_smart_edit(valid_args)
    assert result is True, f"Expected True, got {result}"
    print("✅ Validation test passed")

def test_edit_strategies():
    """Test the edit strategy manager."""
    print("🧪 Testing edit strategies...")
    
    manager = EditStrategyManager()
    
    # Test context-based edit
    content = "line1\nold_line\nline3"
    changes = [{
        "context": ["old_line"],
        "replacement": ["new_line"]
    }]
    
    new_content, results = manager.apply_changes(content, changes)
    assert "new_line" in new_content, "Context edit failed"
    print("✅ Context edit test passed")
    
    # Test line-based edit
    content = "line1\nline2\nline3\nline4"
    changes = [{
        "mode": "line_based",
        "lines": [2, 3],
        "replacement": "replaced_line\n"
    }]
    
    new_content, results = manager.apply_changes(content, changes)
    assert "replaced_line" in new_content, "Line edit failed"
    print("✅ Line edit test passed")

def test_diff_visualizer():
    """Test the diff visualizer."""
    print("🧪 Testing diff visualizer...")
    
    visualizer = DiffVisualizer()
    original = "line1\nline2\nline3"
    modified = "line1\nmodified_line2\nline3"
    
    diff = visualizer.show_rich_diff("test.txt", original, modified)
    assert "modified_line2" in diff, "Diff visualization failed"
    print("✅ Diff visualizer test passed")

def test_backup_manager():
    """Test the backup manager."""
    print("🧪 Testing backup manager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            manager = BackupManager(backup_dir=temp_dir)
            backup_path = manager.create_backup(temp_file)
            assert backup_path is not None, "Backup creation failed"
            assert os.path.exists(backup_path), "Backup file not created"
            print("✅ Backup manager test passed")
        finally:
            os.unlink(temp_file)

def test_full_workflow():
    """Test a complete smart edit workflow."""
    print("🧪 Testing full workflow...")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("def old_function():\n    pass\n\n# Another line\n")
        temp_file = f.name
    
    try:
        # Test smart edit
        args = {
            "file_path": temp_file,
            "changes": [{
                "context": ["def old_function():", "    pass"],
                "replacement": ["def new_function():", "    return True"]
            }],
            "auto_confirm": True,
            "create_backup": True
        }
        
        result = smart_edit_handler(args)
        assert "Successfully edited" in result, f"Edit failed: {result}"
        
        # Verify the changes
        with open(temp_file, 'r') as f:
            content = f.read()
            assert "new_function" in content, "Changes not applied"
            assert "return True" in content, "Changes not applied"
        
        print("✅ Full workflow test passed")
        
    finally:
        os.unlink(temp_file)

def main():
    """Run all tests."""
    print("🚀 Running Smart Edit Tool Plugin Tests\n")
    
    try:
        test_validation()
        test_edit_strategies()
        test_diff_visualizer()
        test_backup_manager()
        test_full_workflow()
        
        print("\n🎉 All tests passed! The Smart Edit Tool Plugin is working correctly.")
        
        print("\n📋 Plugin Features:")
        print("   ✅ Multiple editing strategies (context, line, pattern, semantic)")
        print("   ✅ Rich diff visualization with color coding")
        print("   ✅ Automatic backup creation with rollback")
        print("   ✅ Comprehensive validation and error handling")
        print("   ✅ Integration with AI Coder's tool system")
        
        print("\n🔧 Installation Instructions:")
        print("   1. Copy smart_edit.py to ~/.config/aicoder/plugins/")
        print("   2. Restart AI Coder")
        print("   3. Use the smart_edit tool with your file operations")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()