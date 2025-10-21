#!/usr/bin/env python3
"""
Comprehensive Integration Test Runner for AI Coder.
This script runs comprehensive integration tests that verify real functionality
using actual components and local servers (not unit tests).
"""

import subprocess
import sys
import os
import shutil


def run_test(name, script, timeout=60):
    """Run a test script and return success/failure."""
    print(f"🧪 Running {name}...")
    try:
        # Set environment for subprocess
        env = os.environ.copy()
        # Clear API-related environment to ensure tests use local servers
        for key in list(env.keys()):
            if key.startswith('API_') or key.startswith('OPENAI_') or key in ['ANTHROPIC_API_KEY']:
                del env[key]
        # Ensure YOLO_MODE is set for tests
        env['YOLO_MODE'] = '1'
        
        result = subprocess.run([sys.executable, script],
                              capture_output=True,
                              text=True,
                              timeout=timeout,
                              env=env)
        success = result.returncode == 0
        if success:
            print(f"✅ {name} PASSED")
        else:
            print(f"❌ {name} FAILED")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
        return success
    except subprocess.TimeoutExpired:
        print(f"⏰ {name} TIMED OUT")
        return False
    except Exception as e:
        print(f"💥 {name} ERROR: {e}")
        return False


def main():
    print("🚀 AI Coder - Comprehensive Integration Test Runner")
    print("=" * 50)
    print("⚠️  NOTE: This runs comprehensive INTEGRATION tests only")
    print("   NOT the main unit test suite (use 'bash run-tests.sh' for that)")
    print()

    # List of comprehensive integration tests to run
    tests = [
        ("Streaming Adapter Comprehensive Test", "tests/comprehensive/streaming_adapter_comprehensive_test.py", 60),
        ("Animator and ESC Functionality Test", "tests/comprehensive/animator_esc_functionality_test.py", 30),
        ("Animation Lifecycle Verification", "tests/comprehensive/animation_lifecycle_verification.py", 15),
    ]

    # Optional advanced tests
    advanced_tests = [
        ("TMUX Animator Test", "tests/comprehensive/tmux_animator_esc_test.py", 30),
        ("TMUX ESC Cancellation Test", "tests/comprehensive/tmux_esc_cancellation_test.py", 30),
    ]

    results = []

    print("\\n📋 Running Comprehensive Integration Tests...")
    print("-" * 30)

    for name, script, timeout in tests:
        success = run_test(name, script, timeout)
        results.append((name, success))

    print("\\n📊 Comprehensive Test Results:")
    print("-" * 30)
    comprehensive_passed = 0
    comprehensive_total = len(results)

    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{name}: {status}")
        if success:
            comprehensive_passed += 1

    print(f"\\nComprehensive Tests: {comprehensive_passed}/{comprehensive_total}")

    # Check if tmux is available and run advanced tests automatically
    tmux_available = shutil.which('tmux') is not None

    if tmux_available:
        print("\\n📋 Running Advanced Tests (TMUX available)...")
        print("-" * 30)

        advanced_results = []
        for name, script, timeout in advanced_tests:
            success = run_test(name, script, timeout)
            advanced_results.append((name, success))

        print("\\n📊 Advanced Test Results:")
        print("-" * 30)
        advanced_passed = 0
        advanced_total = len(advanced_results)

        for name, success in advanced_results:
            status = "PASS" if success else "FAIL"
            print(f"{name}: {status}")
            if success:
                advanced_passed += 1

        print(f"\\nAdvanced Tests: {advanced_passed}/{advanced_total}")
    else:
        print("\\n⏭️  TMUX not found, skipping advanced tests")
        advanced_passed = 0
        advanced_total = 0

    print("\\n" + "=" * 50)
    print("🏁 Test Runner Complete")

    total_passed = comprehensive_passed + advanced_passed
    total_tests = comprehensive_total + advanced_total

    print(f"Comprehensive Tests: {comprehensive_passed}/{comprehensive_total}")
    if advanced_total > 0:
        print(f"Advanced Tests: {advanced_passed}/{advanced_total}")
    print(f"Overall: {total_passed}/{total_tests}")

    if comprehensive_passed == comprehensive_total:
        print("\\n🎉 All comprehensive tests PASSED! Application is working correctly.")
        return 0
    else:
        print("\\n❌ Some comprehensive tests FAILED! Application may have issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
