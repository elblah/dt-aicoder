#!/usr/bin/env python3
"""
Script to build a zipapp version of AI Coder for easy distribution.
"""

import os
import shutil
import zipfile


def build_zipapp():
    """Build a zipapp version of AI Coder."""
    # Create a temporary directory for building
    if os.path.exists("build"):
        shutil.rmtree("build")
    os.makedirs("build")

    # Copy the aicoder package
    shutil.copytree("aicoder", "build/aicoder")

    # Copy the main entry point
    shutil.copy("aicoder.py", "build/__main__.py")

    # Create the zipapp
    with zipfile.ZipFile("aicoder.pyz", "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all files from the build directory, excluding cache files
        for root, dirs, files in os.walk("build"):
            # Remove __pycache__ directories to avoid including compiled Python files
            dirs[:] = [d for d in dirs if d != "__pycache__"]

            for file in files:
                # Skip .pyc files as well
                if file.endswith(".pyc"):
                    continue

                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, "build")
                zf.write(file_path, arc_path)

    # Clean up
    shutil.rmtree("build")

    # Make it executable
    os.chmod("aicoder.pyz", 0o755)

    print("Zipapp created: aicoder.pyz")
    print("Run with: python aicoder.pyz")


if __name__ == "__main__":
    build_zipapp()
