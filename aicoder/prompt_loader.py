"""
Prompt loader for AI Coder with environment variable overrides.

This module provides a centralized way to load prompts with support for
environment variable overrides. Users can either provide file paths or
direct prompt content via environment variables.

Supported environment variables:
- AICODER_PROMPT_MAIN: Main system prompt (replaces AICODER.md)
- AICODER_PROMPT_PLAN: Planning mode prompt (replaces plan.md)
- AICODER_PROMPT_BUILD_SWITCH: Build switch prompt (replaces build-switch.md)
- AICODER_PROMPT_COMPACTION: Compaction/summarization prompt (replaces compaction.md)
- AICODER_PROMPT_PROJECT: Project-specific context file (replaces AGENTS.md)
"""

import os
import sys
from typing import Optional

from . import config


def _load_default_prompt(prompt_name: str) -> Optional[str]:
    """
    Load default prompt content from the prompts directory, handling all execution scenarios.
    
    This function mimics the robust loading logic used for AICODER.md to handle:
    - Regular installation
    - Development setup
    - Zipapp execution
    - Package data access
    
    Args:
        prompt_name: Name of the prompt file (without extension)
        
    Returns:
        Prompt content as string, or None if not found
    """
    prompt_filename = f"{prompt_name}.md"
    
    # List of possible locations for prompt files (mirroring AICODER.md logic)
    possible_paths = []

    # 1. Same directory as this file (regular installation)
    possible_paths.append(os.path.join(os.path.dirname(__file__), "prompts", prompt_filename))

    # 2. In current working directory's aicoder folder
    possible_paths.append(os.path.join(os.getcwd(), "aicoder", "prompts", prompt_filename))

    # 3. Relative path from current file
    possible_paths.append(
        os.path.join(os.path.dirname(__file__), "..", "aicoder", "prompts", prompt_filename)
    )

    # 4. In the same directory as the script being run
    try:
        possible_paths.append(
            os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                "aicoder",
                "prompts",
                prompt_filename,
            )
        )
    except Exception:
        pass

    # Try each path
    for path in possible_paths:
        try:
            # Normalize the path
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                with open(normalized_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        if config.DEBUG:
                            print(
                                f"{config.GREEN} *** Found {prompt_filename} at: {normalized_path}{config.RESET}"
                            )
                        return content
        except Exception as e:
            if config.DEBUG:
                print(
                    f"{config.RED} *** Error reading {prompt_filename} from {path}: {e}{config.RESET}"
                )
            continue

    # Special handling for zipapp - try to read from the package directly
    try:
        # When running as a zipapp, we can try to read the file directly from the package
        import pkgutil

        # Try different package names that might be used
        package_names = ["aicoder", "aicoder.aicoder"]
        for package_name in package_names:
            try:
                data = pkgutil.get_data(package_name, f"prompts/{prompt_filename}")
                if data:
                    content = data.decode("utf-8").strip()
                    if content:
                        if config.DEBUG:
                            print(
                                f"{config.GREEN} *** Found {prompt_filename} in package data ({package_name}){config.RESET}"
                            )
                        return content
            except Exception:
                continue
    except Exception as e:
        if config.DEBUG:
            print(
                f"{config.RED} *** Error reading {prompt_filename} from package data: {e}{config.RESET}"
            )

    # Additional zipapp handling - try to read from sys.path
    try:
        if hasattr(sys, "path") and sys.path:
            for path_entry in sys.path:
                if path_entry.endswith(".pyz") or path_entry.endswith(".zip"):
                    # This might be a zipapp, try to read from it
                    try:
                        import zipfile

                        with zipfile.ZipFile(path_entry, "r") as zf:
                            # Try different possible paths within the zip
                            possible_zip_paths = [
                                f"aicoder/prompts/{prompt_filename}",
                                f"prompts/{prompt_filename}",
                            ]
                            for zip_path in possible_zip_paths:
                                try:
                                    with zf.open(zip_path) as f:
                                        content = f.read().decode("utf-8").strip()
                                        if content:
                                            if config.DEBUG:
                                                print(
                                                    f"{config.GREEN} *** Found {prompt_filename} in zipapp ({path_entry}/{zip_path}){config.RESET}"
                                                )
                                            return content
                                except Exception:
                                    continue
                    except Exception:
                        continue
    except Exception as e:
        if config.DEBUG:
            print(
                f"{config.RED} *** Error reading {prompt_filename} from zipapp: {e}{config.RESET}"
            )

    # If we get here, we couldn't find the prompt file
    if config.DEBUG:
        print(
            f"{config.YELLOW} *** {prompt_filename} not found in any expected location{config.RESET}"
        )
        print(f"{config.YELLOW} *** Searched paths: {possible_paths}{config.RESET}")
    return None


def load_prompt_from_env(env_var_name: str, prompt_name: str) -> str:
    """
    Load prompt content from environment variable with fallback to default file.

    Args:
        env_var_name: Name of the environment variable to check
        prompt_name: Name of the default prompt file (without extension)

    Returns:
        Prompt content as string
    """
    env_value = os.environ.get(env_var_name)
    if not env_value:
        # No environment variable, load from default file
        default_content = _load_default_prompt(prompt_name)
        if default_content:
            if config.DEBUG:
                print(f"{config.GREEN} *** Loaded {prompt_name} from default prompt file{config.RESET}")
            return default_content
        else:
            if config.DEBUG:
                print(f"{config.YELLOW} *** {prompt_name} default file not found{config.RESET}")
            return None

    # Simple heuristic: if it looks like a file path, try reading as file
    # Consider it a path if it contains '/' or starts with '.' or '~'
    if not ('/' in env_value or env_value.startswith(('.', '~'))):
        # Treat as literal prompt content
        if config.DEBUG:
            print(f"{config.GREEN} *** Loaded {prompt_name} from environment variable content{config.RESET}")
        return env_value

    # Try to read as file
    expanded_path = os.path.expanduser(env_value)
    if not os.path.exists(expanded_path):
        if config.DEBUG:
            print(f"{config.YELLOW} *** {env_var_name} file not found: {expanded_path}, treating as literal content{config.RESET}")
        return env_value

    if not os.path.isfile(expanded_path):
        if config.DEBUG:
            print(f"{config.RED} *** {env_var_name} path exists but is not a file: {expanded_path}{config.RESET}")
        # Fall back to default prompt file
        default_content = _load_default_prompt(prompt_name)
        return default_content

    try:
        with open(expanded_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                if config.DEBUG:
                    print(f"{config.GREEN} *** Loaded {prompt_name} from file: {expanded_path}{config.RESET}")
                return content
            else:
                if config.DEBUG:
                    print(f"{config.YELLOW} *** {env_var_name} file is empty, using default{config.RESET}")
                # Fall back to default prompt file
                default_content = _load_default_prompt(prompt_name)
                return default_content
    except Exception as e:
        if config.DEBUG:
            print(f"{config.RED} *** Error reading {env_var_name} file {expanded_path}: {e}, treating as literal content{config.RESET}")
        return env_value


def get_main_prompt() -> str:
    """
    Get the main system prompt with environment variable override and template variables.
    
    Returns:
        Main prompt content as string with template variables applied
        
    Raises:
        SystemExit: If no valid system prompt can be found (fatal error)
    """
    import os
    import sys
    from datetime import datetime
    import platform
    import shutil
    
    # Get the base prompt content
    base_prompt = load_prompt_from_env('AICODER_PROMPT_MAIN', 'main')
    
    # If no prompt was found, this is a fatal error
    if not base_prompt:
        print(f"{config.RED} *** FATAL ERROR: No system prompt found!{config.RESET}", file=sys.stderr)
        print(f"{config.RED} *** AI Coder cannot function without a system prompt.{config.RESET}", file=sys.stderr)
        print(f"{config.RED} *** Please ensure one of the following exists:{config.RESET}", file=sys.stderr)
        print(f"{config.RED} ***   - Set AICODER_PROMPT_MAIN environment variable{config.RESET}", file=sys.stderr)
        print(f"{config.RED} ***   - Place a prompt file at aicoder/prompts/main.md{config.RESET}", file=sys.stderr)
        print(f"{config.RED} ***   - Ensure AICODER.md is available{config.RESET}", file=sys.stderr)
        sys.exit(1)
    
    # Apply template variables if they exist in the prompt
    if '{current_directory}' in base_prompt:
        base_prompt = base_prompt.replace('{current_directory}', os.getcwd())
    
    if '{current_datetime}' in base_prompt:
        current_datetime = datetime.now()
        base_prompt = base_prompt.replace('{current_datetime}', current_datetime.strftime("%Y-%m-%d %H:%M:%S"))
    
    if '{available_tools}' in base_prompt:
        # Detect available tools (same logic as message_history)
        tool_map = {
            "text search": ["rg", "ag", "grep"],
            "file search": ["fd", "rg", "find"],
            "file listing": ["eza", "exa", "ls"],
            "directory tree": ["tree", "eza"],
        }

        available_sections = []
        for category, tools in tool_map.items():
            available = []
            for tool in tools:
                tool_to_check = tool.split()[0] if " " in tool else tool
                if shutil.which(tool_to_check):
                    available.append(tool)
            if available:
                available_sections.append(f"{category}: {', '.join(available)}")

        if available_sections:
            available_tools = (
                "Some commands that are available for certain tasks on this system that you might use:\n"
                + "\n".join(f"- {section}" for section in available_sections)
            )
        else:
            available_tools = "Standard Unix/Linux tools are available on this system."
        
        base_prompt = base_prompt.replace('{available_tools}', available_tools)
    
    if '{system_info}' in base_prompt:
        system = platform.system()
        machine = platform.machine()
        system_info = f"This is a {system} system on {machine} architecture"
        base_prompt = base_prompt.replace('{system_info}', system_info)
    
    return base_prompt


def get_plan_prompt() -> str:
    """
    Get the planning mode prompt with environment variable override.
    
    Returns:
        Plan prompt content as string
    """
    return load_prompt_from_env('AICODER_PROMPT_PLAN', 'plan')


def get_build_switch_prompt() -> str:
    """
    Get the build switch prompt with environment variable override.
    
    Returns:
        Build switch prompt content as string
    """
    return load_prompt_from_env('AICODER_PROMPT_BUILD_SWITCH', 'build-switch')


def get_compaction_prompt() -> str:
    """
    Get the compaction/summarization prompt with environment variable override.
    
    Returns:
        Compaction prompt content as string
    """
    return load_prompt_from_env('AICODER_PROMPT_COMPACTION', 'compaction')


def get_project_filename() -> str:
    """
    Get the project-specific prompt filename from environment variable.
    
    Returns:
        Project filename as string (e.g., "AGENTS.md", "CLAUDE.md", "GEMINI.md")
    """
    project_file = os.environ.get('AICODER_PROMPT_PROJECT', 'AGENTS.md')
    
    # Ensure it has .md extension
    if not project_file.endswith('.md'):
        project_file += '.md'
    
    if config.DEBUG:
        print(f"{config.GREEN} *** Using project prompt file: {project_file}{config.RESET}")
    
    return project_file