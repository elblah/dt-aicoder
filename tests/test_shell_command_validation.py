"""
Unit tests for shell command validation functionality.
"""

import sys
import os

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.tool_manager.internal_tools.run_shell_command import (
    validate_shell_command,
    analyze_command_safety,
    SAFE_READING_COMMANDS,
    DANGEROUS_PATTERNS
)
from aicoder import config


def test_safe_reading_commands_auto_approval():
    """Test that safe reading commands are auto-approved."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        safe_commands = [
            "rg test .",
            "grep pattern file.txt",
            "ls -la",
            "cat file.txt",
            "head -10 file.txt",
            "tail -20 log.txt",
            "find . -name '*.py'",
            "file script.py",
            "wc -l file.txt",
            "du -sh .",
            "stat file.txt",
            "whoami",
            "pwd",
            "date",
            "which python",
            "whereis python",
            "type python",
            "echo hello",
            "printf 'hello'",
            "basename /path/to/file.txt",
            "dirname /path/to/file.txt",
            "realpath ./file.txt",
            "readlink /usr/bin/python"
        ]
        
        for cmd in safe_commands:
            result = validate_shell_command({"command": cmd})
            assert result is True, f"Command '{cmd}' should be auto-approved"
    finally:
        config.YOLO_MODE = original_yolo


def test_dangerous_patterns_require_approval():
    """Test that commands with dangerous patterns require manual approval."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        dangerous_commands = [
            # Pipes and command chaining
            "ls | head -5",                        # Pipe
            "python -V | grep Python",             # Pipe with python
            "python -V && uname",                  # Logical AND
            "python -V || echo failed",            # Logical OR
            "make && echo success",                 # Logical AND (different command)
            "make || echo fail",                    # Logical OR (different command)
            
            # Command separators
            "rm file.txt; echo done",              # Command separator
            "python -V; uname",                    # Command separator with python
            "pwd; date",                           # Multiple command separators
            
            # Command substitution
            "echo $(date)",                         # Command substitution $(...)
            "echo `date`",                          # Backtick command substitution
            "python -c \"print($(whoami))\"",       # Command substitution in python
            
            # Redirects
            "echo test > file.txt",                 # Output redirect
            "cat < file.txt",                       # Input redirect
            "echo test >> file.txt",                # Append redirect
            "python -V > /tmp/output",              # Redirect with python
            
            # Background execution
            "sleep 10 &",                           # Background execution
            "python script.py &",                   # Background python
            
            # Privilege escalation
            "sudo rm -rf /",                        # sudo usage
            "su - root",                            # su usage
            "sudo python script.py",                # sudo with python
            
            # Multiple dangerous patterns
            "python -c 'code' | grep .",            # Multiple patterns
            "python -V; uname && date",             # Multiple patterns
            "sudo python script.py > output.txt &", # Multiple patterns
        ]
        
        for cmd in dangerous_commands:
            result = validate_shell_command({"command": cmd})
            assert result is True, f"Command '{cmd}' should proceed to normal approval"
    finally:
        config.YOLO_MODE = original_yolo


def test_comprehensive_dangerous_patterns():
    """Test comprehensive dangerous pattern detection with analyze_command_safety."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        dangerous_cases = [
            # Basic dangerous patterns
            ("python -V; uname", "Dangerous pattern detected: ;"),
            ("python -V && uname", "Dangerous pattern detected: &&"),
            ("python -V || echo failed", "Dangerous pattern detected: \\|"),
            ("python -V | grep Python", "Dangerous pattern detected: \\|"),
            ("echo $(python -V)", "Dangerous pattern detected: \\$\\("),
            ("sudo rm -rf /", "Dangerous pattern detected: \\s*sudo\\s+"),
            ("python -V > /tmp/output", "Dangerous pattern detected: >"),
            ("sleep 10 &", "requires manual approval"),
            ("su - root", "Dangerous pattern detected: \\s*su\\s+"),
        ]
        
        for cmd, expected_reason_pattern in dangerous_cases:
            is_safe, reason, main_cmd = analyze_command_safety(cmd)
            assert not is_safe, f"Command '{cmd}' should be detected as dangerous"
            assert "requires manual approval" in reason or "Dangerous pattern detected" in reason
            # Check that the specific pattern is mentioned
            assert any(pattern in reason for pattern in expected_reason_pattern.split()), \
                  f"Reason '{reason}' should contain pattern from '{expected_reason_pattern}'"
    finally:
        config.YOLO_MODE = original_yolo


def test_semicolon_context_detection():
    """Test that semicolons in Python strings are safe but as command separators are dangerous."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        # Safe: semicolons in Python strings/code
        safe_commands = [
            'python -c "print(\\"hello\\"); print(\\"world\\")"',
            "python -c 'print(\'hello\'); print(\'world\')'",
            'python -c "import sys; print(sys.version)"',
        ]
        
        for cmd in safe_commands:
            result = validate_shell_command({"command": cmd})
            assert result is True, f"Command '{cmd}' should be safe (semicolons in Python strings)"
        
        # Dangerous: semicolons as command separators
        dangerous_commands = [
            "echo hello; echo world",
            "ls; echo done",
            "pwd; date",
        ]
        
        for cmd in dangerous_commands:
            result = validate_shell_command({"command": cmd})
            assert result is True, f"Command '{cmd}' should proceed to normal approval (command separator)"
    finally:
        config.YOLO_MODE = original_yolo


def test_regular_commands_normal_approval():
    """Test that regular non-reading commands go to normal approval."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        regular_commands = [
            "python script.py",
            "npm install",
            "make build",
            "cargo run",
            "docker build .",
            "git commit -m 'test'",
            "pytest test_file.py"
        ]
        
        for cmd in regular_commands:
            result = validate_shell_command({"command": cmd})
            assert result is True, f"Command '{cmd}' should proceed to normal approval"
    finally:
        config.YOLO_MODE = original_yolo


def test_edge_cases():
    """Test edge cases and error conditions."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        # Empty command
        result = validate_shell_command({"command": ""})
        assert isinstance(result, str), "Empty command should return error message"
        assert "Empty command" in result
        
        # Whitespace only
        result = validate_shell_command({"command": "   "})
        assert isinstance(result, str), "Whitespace-only command should return error message"
        assert "Empty command" in result
    finally:
        config.YOLO_MODE = original_yolo


def test_analyze_command_safety_function():
    """Test the analyze_command_safety helper function."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        # Safe reading command
        is_safe, reason, main_cmd = analyze_command_safety("ls -la")
        assert is_safe
        assert "Safe reading command" in reason
        assert main_cmd == "ls"
        
        # Command with dangerous pattern
        is_safe, reason, main_cmd = analyze_command_safety("ls | head")
        assert not is_safe
        assert "Dangerous pattern" in reason
        assert main_cmd == "ls"
        
        # Regular command
        is_safe, reason, main_cmd = analyze_command_safety("python script.py")
        assert not is_safe
        assert "requires manual approval" in reason
        assert main_cmd == "python"
        
        # YOLO mode
        is_safe, reason, main_cmd = analyze_command_safety("rm -rf /", yolo_mode=True)
        assert is_safe
        assert "YOLO mode" in reason
    finally:
        config.YOLO_MODE = original_yolo


def test_command_parsing():
    """Test that command parsing works correctly with various formats."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        test_cases = [
            ("ls -la", "ls"),
            ("/usr/bin/python script.py", "python"),
            ("./script.sh", "script.sh"),
            ("python -c 'print(\"hello\")'", "python"),
            ("git", "git"),
        ]
        
        for cmd, expected_main in test_cases:
            is_safe, reason, main_cmd = analyze_command_safety(cmd)
            assert main_cmd == expected_main
    finally:
        config.YOLO_MODE = original_yolo


def test_safe_reading_commands_set():
    """Test that the safe reading commands set contains expected commands."""
    expected_safe_commands = {
        'rg', 'grep', 'ls', 'cat', 'head', 'tail', 'find', 'file', 'wc', 'du',
        'stat', 'whoami', 'pwd', 'date', 'which', 'whereis', 'type', 'echo',
        'printf', 'basename', 'dirname', 'realpath', 'readlink'
    }
    assert SAFE_READING_COMMANDS == expected_safe_commands


def test_dangerous_patterns():
    """Test that dangerous patterns are correctly defined."""
    assert any(pattern == r'\|' for pattern in DANGEROUS_PATTERNS)
    assert any(pattern == r'\$\(' for pattern in DANGEROUS_PATTERNS)
    assert any('sudo' in pattern for pattern in DANGEROUS_PATTERNS)


def test_simulated_aicoder_session_flow():
    """Test a simulated AI Coder session with approval flow."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        # Mock approval system and session cache
        from aicoder.tool_manager.approval_system import ApprovalSystem
        from aicoder.tool_manager.internal_tools.run_shell_command import (
            get_dynamic_tool_config, has_dangerous_patterns
        )
        
        # Create a mock approval system
        class MockStats:
            pass
        
        class MockAnimator:
            def start_cursor_blinking(self):
                pass
            def stop_cursor_blinking(self):
                pass
        
        class MockToolRegistry:
            pass
        
        approval_system = ApprovalSystem(MockToolRegistry(), MockStats(), MockAnimator())
        
        # Simulate the session flow
        session_commands = [
            # 1. ls - should be auto-approved (safe reading command)
            ("ls -la", "ls", True, False, "ls should be auto-approved"),
            
            # 2. python -V - should ask for approval first time
            ("python -V", "python", False, False, "python should ask for approval first time"),
            
            # 3. python -V again - should still ask for approval (not session approved yet)
            ("python -V", "python", False, False, "python should still ask for approval"),
            
            # 4. python -V again - user approves for session this time
            ("python -V", "python", False, True, "python approved for session"),
            
            # 5. python -V again - should be auto-approved (session approved)
            ("python -V", "python", True, False, "python should be auto-approved after session approval"),
            
            # 6. python -V; uname - should NOT be auto-approved (dangerous pattern)
            ("python -V; uname", "python", False, False, "python with semicolon should require approval despite session"),
        ]
        
        for cmd, expected_main_cmd, should_auto_approve, user_approves_session, description in session_commands:
            arguments = {"command": cmd}
            
            # Test 1: Check if command has dangerous patterns
            has_dangerous, reason = has_dangerous_patterns(cmd)
            
            # Test 2: Get dynamic tool config
            base_config = {
                "type": "internal",
                "auto_approved": False,
                "approval_excludes_arguments": False,
            }
            dynamic_config = get_dynamic_tool_config(base_config, arguments)
            
            # Test 3: Parse main command
            import shlex
            try:
                parts = shlex.split(cmd.strip())
                if parts:
                    main_command = parts[0].split('/')[-1]
                else:
                    main_command = ""
            except (ValueError, shlex.SplitError):
                main_command = cmd.split()[0].split('/')[-1] if cmd else ""
            
            assert main_command == expected_main_cmd, f"Main command mismatch for '{cmd}'"
            
            # Test 4: Check auto-approval logic
            if has_dangerous:
                # Dangerous patterns should never be auto-approved
                assert not dynamic_config.get("auto_approved", False), \
                      f"Command with dangerous pattern should not be auto-approved: {cmd}"
            elif main_command in SAFE_READING_COMMANDS:
                # Safe reading commands should always be auto-approved
                assert dynamic_config.get("auto_approved", False), \
                     f"Safe reading command should be auto-approved: {cmd}"
            else:
                # Other commands depend on session approval
                cache_key = f"run_shell_command:{main_command}"
                was_session_approved = cache_key in approval_system.tool_approvals_session
                
                if should_auto_approve and not has_dangerous:
                    assert dynamic_config.get("auto_approved", False) or was_session_approved, \
                          f"Session-approved command should be auto-approved: {cmd}"
            
            # Test 5: Simulate session approval
            if user_approves_session and not has_dangerous:
                cache_key = f"run_shell_command:{main_command}"
                approval_system.tool_approvals_session.add(cache_key)
    finally:
        config.YOLO_MODE = original_yolo


def test_edge_cases_and_boundary_conditions():
    """Test edge cases and boundary conditions."""
    # Ensure YOLO mode is disabled for testing
    original_yolo = config.YOLO_MODE
    config.YOLO_MODE = False
    
    try:
        edge_cases = [
            # Empty and whitespace commands
            ("", "", "Empty command should be rejected"),
            ("   ", "", "Whitespace-only command should be rejected"),
            
            # Commands with complex paths
            ("/usr/bin/python -c 'print(\"hello\")'", "python", "Complex path should extract command correctly"),
            ("./script.sh", "script.sh", "Relative path should extract command correctly"),
            ("../python -V", "python", "Parent directory path should extract command correctly"),
            
            # Commands with quotes and special characters
            ('python -c "print(\\"hello world\\")"', "python", "Python with escaped quotes should work"),
            ("python -c 'print(\"hello\")'", "python", "Python with mixed quotes should work"),
            ('bash -c "echo \\"test\\""', "bash", "Bash with nested quotes should work"),
            
            # Multiple spaces and tabs
            ("python    -V", "python", "Multiple spaces should be handled"),
            ("python\t-V", "python", "Tabs should be handled"),
            ("python   -c    'print()'", "python", "Mixed spacing should be handled"),
        ]
        
        for cmd, expected_main_cmd, description in edge_cases:
            if not cmd.strip():  # Skip empty commands for main command extraction
                continue
                
            # Test main command extraction
            import shlex
            try:
                parts = shlex.split(cmd.strip())
                if parts:
                    main_command = parts[0].split('/')[-1]
                else:
                    main_command = ""
            except (ValueError, shlex.SplitError):
                main_command = cmd.split()[0].split('/')[-1] if cmd else ""
            
            assert main_command == expected_main_cmd, \
                  f"Main command extraction failed for '{cmd}': expected '{expected_main_cmd}', got '{main_command}'"
    finally:
        config.YOLO_MODE = original_yolo