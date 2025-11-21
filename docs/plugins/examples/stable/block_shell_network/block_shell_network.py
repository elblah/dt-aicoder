"""
Block Shell Network Plugin for AI Coder

This plugin provides network sandboxing for shell commands using seccomp:
1. Compiles a seccomp C program to block network syscalls
2. Intercepts run_shell_command calls to prepend the network blocker
3. Provides /net command to enable/disable network blocking
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Plugin configuration
PLUGIN_NAME = "block_shell_network"
PLUGIN_VERSION = "1.0.0"

# Network blocking state (default: disabled)
_network_blocking_enabled = False
_blocknet_executable_path = None
_compilation_in_progress = False
_requirements_checked = False
_missing_requirements = []

# Global reference to aicoder instance
_aicoder_ref = None

# C source code for the network blocker
SECCOMP_SOURCE = '''
/*
 * Minimal Network Blocker using libseccomp
 *
 * Blocks network syscalls on any architecture
 * Uses switch instead of array to avoid SCMP_SYS macro issues
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/prctl.h>
#include <seccomp.h>

static int install_network_filter(void) {
    scmp_filter_ctx ctx;
    int rc;

    ctx = seccomp_init(SCMP_ACT_ALLOW);
    if (!ctx) {
        perror("seccomp_init failed");
        return -1;
    }

    // Block network syscalls - explicit calls for portability
    #define BLOCK_SYSCALL(name) do { \\
        rc = seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EACCES), SCMP_SYS(name), 0); \\
        if (rc != 0 && rc != -EDOM) { \\
            fprintf(stderr, "Failed to block %s: %s\\n", #name, strerror(-rc)); \\
            seccomp_release(ctx); \\
            return -1; \\
        } \\
    } while(0)

    BLOCK_SYSCALL(socket);
    BLOCK_SYSCALL(connect);
    BLOCK_SYSCALL(bind);
    BLOCK_SYSCALL(listen);
    BLOCK_SYSCALL(accept);
    BLOCK_SYSCALL(accept4);
    BLOCK_SYSCALL(sendto);
    BLOCK_SYSCALL(recvfrom);
    BLOCK_SYSCALL(sendmsg);
    BLOCK_SYSCALL(recvmsg);
    BLOCK_SYSCALL(sendmmsg);
    BLOCK_SYSCALL(recvmmsg);
    BLOCK_SYSCALL(socketcall);

    #undef BLOCK_SYSCALL

    // Load the filter
    rc = seccomp_load(ctx);
    if (rc != 0) {
        fprintf(stderr, "Failed to load seccomp filter: %s\\n", strerror(-rc));
        seccomp_release(ctx);
        return -1;
    }

    seccomp_release(ctx);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <command> [args...]\\n", argv[0]);
        return 1;
    }

    if (install_network_filter() != 0) {
        fprintf(stderr, "Failed to install network filter\\n");
        return 1;
    }

    execvp(argv[1], argv + 1);
    perror("execvp failed");
    return 1;
}
'''


def check_requirements() -> tuple[bool, list[str]]:
    """Check if required dependencies are available."""
    global _requirements_checked, _missing_requirements

    if _requirements_checked:
        return len(_missing_requirements) == 0, _missing_requirements

    _missing_requirements = []
    
    # Check for seccomp header
    seccomp_paths = [
        "/usr/include/seccomp.h",
        "/usr/local/include/seccomp.h",
        "/usr/include/x86_64-linux-gnu/seccomp.h",
    ]
    
    seccomp_found = any(os.path.exists(path) for path in seccomp_paths)
    if not seccomp_found:
        _missing_requirements.append("libseccomp-dev (install with: apt install libseccomp-dev)")
    
    # Check for gcc
    if not shutil.which("gcc"):
        _missing_requirements.append("gcc (install with: apt install build-essential)")
    
    _requirements_checked = True
    
    return len(_missing_requirements) == 0, _missing_requirements


def compile_blocknet_executable() -> str | None:
    """Compile the seccomp network blocker executable."""
    global _blocknet_executable_path, _compilation_in_progress

    if _blocknet_executable_path and os.path.exists(_blocknet_executable_path):
        return _blocknet_executable_path

    if _compilation_in_progress:
        return None

    # Check requirements first
    requirements_ok, missing = check_requirements()
    if not requirements_ok:
        print(f"[X] Network blocking unavailable - missing requirements:")
        for req in missing:
            print(f"    - {req}")
        return None

    _compilation_in_progress = True
    
    try:
        # Create temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = os.path.join(temp_dir, "block_network_seccomp.c")
            executable_file = os.path.join(temp_dir, "block-net")
            
            # Write source code
            with open(source_file, "w") as f:
                f.write(SECCOMP_SOURCE)
            
            # Compile
            compile_cmd = [
                "gcc",
                "-o", executable_file,
                source_file,
                "-lseccomp"
            ]
            
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"[X] Failed to compile network blocker:")
                print(f"    stderr: {result.stderr.strip()}")
                print(f"    stdout: {result.stdout.strip()}")
                return None
            
            # Move to permanent location in /tmp
            permanent_path = "/tmp/block-net-aicoder"
            shutil.move(executable_file, permanent_path)
            os.chmod(permanent_path, 0o755)  # Make executable
            
            _blocknet_executable_path = permanent_path
            print(f"[+] Network blocker compiled successfully: {permanent_path}")
            return permanent_path
            
    except Exception as e:
        print(f"[X] Failed to compile network blocker: {e}")
        return None
    finally:
        _compilation_in_progress = False


def get_network_blocking_status() -> bool:
    """Get current network blocking status."""
    return _network_blocking_enabled


def set_network_blocking_status(enabled: bool) -> bool:
    """Set network blocking status."""
    global _network_blocking_enabled
    
    if enabled:
        # Just enable the flag - compilation will happen lazily on first use
        _network_blocking_enabled = True
        print("[+] Network sandbox enabled")
        print("    [INFO] Seccomp binary will be compiled on first shell command")
    else:
        _network_blocking_enabled = False
        print("[-] Network sandbox disabled")
    
    return True


def patch_run_shell_command():
    """Patch the run_shell_command tool to prepend network blocker."""
    # Import here to avoid circular imports
    from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS
    
    # Store original execute function
    original_execute = INTERNAL_TOOL_FUNCTIONS.get("run_shell_command")
    
    def patched_execute(command, stats, reason=None, timeout=None, **kwargs):
        """Execute shell command with optional network blocking."""
        global _network_blocking_enabled, _blocknet_executable_path
        
        # If network sandbox is enabled
        if _network_blocking_enabled:
            # Compile the executable if needed (lazy compilation)
            if not _blocknet_executable_path or not os.path.exists(_blocknet_executable_path):
                executable = compile_blocknet_executable()
                if not executable:
                    # Compilation failed - fall back to normal execution with warning
                    print("[WARNING] Network sandbox unavailable - running without network blocking")
                    return original_execute(command, stats, reason, timeout, **kwargs)
            
            # Prepend the network blocker to the command
            wrapped_command = f'{_blocknet_executable_path} bash -c "{command}"'
            return original_execute(wrapped_command, stats, reason, timeout, **kwargs)
        else:
            # Normal execution
            return original_execute(command, stats, reason, timeout, **kwargs)
    
    # Replace the function
    INTERNAL_TOOL_FUNCTIONS["run_shell_command"] = patched_execute


# Command alias for /snet
SANDBOX_COMMAND_ALIAS = "/snet"


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference for later use
        global _aicoder_ref
        _aicoder_ref = aicoder_instance
        
        # Register command handlers
        aicoder_instance.command_handlers["/sandbox-net"] = _handle_sandbox_command
        aicoder_instance.command_handlers["/snet"] = _handle_sandbox_command
        
        # Patch run_shell_command to intercept calls
        patch_run_shell_command()
        
        print("[+] Network sandbox plugin initialized")
        print("    Use /sandbox-net on|off to control network access for shell commands")
        print("    Default: sandbox disabled (network access allowed)")
        
        # Check requirements on startup
        requirements_ok, missing = check_requirements()
        if not requirements_ok:
            print("    [WARNING] Missing requirements for network sandbox:")
            for req in missing:
                print(f"        - {req}")
        else:
            print("    [INFO] Requirements satisfied - network sandbox available")
        
        return True
    except Exception as e:
        print(f"[X] Failed to load network sandbox plugin: {e}")
        return False


def _handle_sandbox_command(args):
    """Handle /sandbox-net command - show status or manage sandbox settings."""
    if not args:
        # Show current status
        status = "enabled" if get_network_blocking_status() else "disabled"
        print(f"Network sandbox: {status}")
        return False, False
    
    if len(args) == 1:
        arg = args[0].lower()
        if arg in ["on", "enable", "true", "1"]:
            set_network_blocking_status(True)
        elif arg in ["off", "disable", "false", "0"]:
            set_network_blocking_status(False)
        elif arg in ["help", "-h", "--help"]:
            _show_help()
        elif arg in ["status", "show"]:
            status = "enabled" if get_network_blocking_status() else "disabled"
            print(f"Network sandbox: {status}")
        else:
            print(f"Unknown option: {arg}")
            _show_help()
    else:
        _show_help()
    
    return False, False


def _show_help():
    """Show help for /sandbox-net command."""
    print("/sandbox-net usage:")
    print("  /sandbox-net              - Show status")
    print("  /sandbox-net on           - Enable network sandbox")
    print("  /sandbox-net off          - Disable network sandbox")
    print("  /sandbox-net help         - Show this help")
    print("")
    print("Default: disabled (network access allowed)")
    print("Alias: /snet")


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference for later use
        global _aicoder_ref
        _aicoder_ref = aicoder_instance
        
        # Register command handlers
        aicoder_instance.command_handlers["/sandbox-net"] = _handle_sandbox_command
        aicoder_instance.command_handlers["/snet"] = _handle_sandbox_command
        
        # Patch run_shell_command to intercept calls
        patch_run_shell_command()
        
        print("[+] Network sandbox plugin initialized")
        print("    Use /sandbox-net on|off to control network access for shell commands")
        print("    Default: sandbox disabled (network access allowed)")
        
        # Check requirements on startup
        requirements_ok, missing = check_requirements()
        if not requirements_ok:
            print("    [WARNING] Missing requirements for network sandbox:")
            for req in missing:
                print(f"        - {req}")
        else:
            print("    [INFO] Requirements satisfied - network sandbox available")
        
        return True
    except Exception as e:
        print(f"[X] Failed to load network sandbox plugin: {e}")
        return False


# Plugin metadata
__plugin_name__ = PLUGIN_NAME
__plugin_version__ = PLUGIN_VERSION
__plugin_description__ = "Network sandboxing for shell commands using seccomp"