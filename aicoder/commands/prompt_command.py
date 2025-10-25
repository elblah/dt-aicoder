"""
Prompt command for AI Coder.
"""

import os
import subprocess
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import wmsg, imsg, emsg
from pathlib import Path


class PromptCommand(BaseCommand):
    """Handle prompt commands - display current prompt, list available, or set active prompt."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/prompt"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle prompt commands - display current prompt, list available, or set active prompt."""
        from ..prompt_loader import (
            get_main_prompt,
            get_plan_prompt,
            get_build_switch_prompt,
            get_compaction_prompt,
            get_project_filename,
        )

        # Check for help argument
        if "help" in args:
            self._show_prompt_help()
            return False, False

        # Handle list subcommand
        if "list" in args:
            self._handle_prompt_list()
            return False, False

        # Handle set subcommand
        if "set" in args:
            return self._handle_prompt_set(args)

        # Handle edit subcommand
        if "edit" in args:
            return self._handle_prompt_edit(args)

        # Handle reset subcommand
        if "reset" in args:
            return self._handle_prompt_reset(args)

        # Check if full mode is requested
        full_mode = "full" in args

        title = "CURRENT PROMPTS" + (" (FULL)" if full_mode else "")

        # Calculate responsive box width
        try:
            terminal_width = os.get_terminal_size().columns
            box_width = min(
                int(terminal_width * 0.8), 100
            )  # 80% of terminal width, max 100 chars
        except (OSError, AttributeError):
            box_width = 70  # Fallback width for non-terminal environments

        # Ensure minimum width based on title
        min_width = len(title) + 8  # Add padding
        box_width = max(box_width, min_width)

        top_border = "╔" + "═" * (box_width - 2) + "╗"
        bottom_border = "╚" + "═" * (box_width - 2) + "╝"

        print(f"\n{config.BOLD}{config.CYAN}{top_border}{config.RESET}")
        print(
            f"{config.BOLD}{config.CYAN}║ {title.center(box_width - 4)} ║{config.RESET}"
        )
        print(f"{config.BOLD}{config.CYAN}{bottom_border}{config.RESET}\n")

        # Main System Prompt
        main_source = (
            "Environment Variable"
            if os.environ.get("AICODER_PROMPT_MAIN")
            else "Default File"
        )
        if os.environ.get("AICODER_PROMPT_MAIN"):
            env_value = os.environ["AICODER_PROMPT_MAIN"]
            if "/" in env_value or env_value.startswith((".", "~")):
                main_source = f"File: {env_value}"
            else:
                main_source = "Environment Variable (literal)"

        main_prompt = get_main_prompt()
        imsg(f"{config.BOLD}📋 MAIN SYSTEM PROMPT")
        wmsg(f"   Source: {main_source}")
        wmsg(f"   Length: {len(main_prompt)} characters")
        print(
            f"{config.CYAN}   ──────────────────────────────────────────────────────────────{config.RESET}"
        )
        if full_mode:
            print(f"{config.WHITE}{main_prompt}{config.RESET}\n")
        else:
            print(
                f"{config.WHITE}{main_prompt[:500]}{'...' if len(main_prompt) > 500 else ''}{config.RESET}\n"
            )

        # Project Context File
        project_file = get_project_filename()
        project_source = (
            "Environment Variable"
            if os.environ.get("AICODER_PROMPT_PROJECT")
            else "Default (AGENTS.md)"
        )
        if os.environ.get("AICODER_PROMPT_PROJECT"):
            project_source = f"Environment Variable → {project_file}"

        project_content = ""
        project_files = [project_file, project_file.lower()]
        for proj_file in project_files:
            if os.path.exists(proj_file):
                try:
                    with open(proj_file, "r", encoding="utf-8") as f:
                        project_content = f.read().strip()
                    break
                except Exception:
                    continue

        imsg(f"{config.BOLD}📄 PROJECT CONTEXT FILE")
        wmsg(f"   File: {project_file}")
        wmsg(f"   Source: {project_source}")
        if project_content:
            wmsg("   Status: ✅ Found")
            wmsg(f"   Length: {len(project_content)} characters")
            print(
                f"{config.CYAN}   ──────────────────────────────────────────────────────────────{config.RESET}"
            )
            if full_mode:
                print(f"{config.WHITE}{project_content}{config.RESET}\n")
            else:
                print(
                    f"{config.WHITE}{project_content[:300]}{'...' if len(project_content) > 300 else ''}{config.RESET}\n"
                )
        else:
            wmsg("   Status: ❌ Not found\n")

        # Planning Mode Prompts
        from ..planning_mode import get_planning_mode

        planning_mode = get_planning_mode()

        plan_prompt = get_plan_prompt()
        plan_source = (
            "Environment Variable"
            if os.environ.get("AICODER_PROMPT_PLAN")
            else "Default File"
        )
        if os.environ.get("AICODER_PROMPT_PLAN"):
            env_value = os.environ["AICODER_PROMPT_PLAN"]
            if "/" in env_value or env_value.startswith((".", "~")):
                plan_source = f"File: {env_value}"
            else:
                plan_source = "Environment Variable (literal)"

        imsg(f"{config.BOLD}🎯 PLANNING MODE PROMPT")
        wmsg(f"   Source: {plan_source}")
        wmsg(
            f"   Status: {'🟢 ACTIVE' if planning_mode.is_plan_mode_active() else '⚪ INACTIVE'}"
        )
        wmsg(f"   Length: {len(plan_prompt)} characters")
        print(
            f"{config.CYAN}   ──────────────────────────────────────────────────────────────{config.RESET}"
        )
        if full_mode:
            print(f"{config.WHITE}{plan_prompt}{config.RESET}\n")
        else:
            print(
                f"{config.WHITE}{plan_prompt[:300]}{'...' if len(plan_prompt) > 300 else ''}{config.RESET}\n"
            )

        # Build Switch Prompt
        build_prompt = get_build_switch_prompt()
        build_source = (
            "Environment Variable"
            if os.environ.get("AICODER_PROMPT_BUILD_SWITCH")
            else "Default File"
        )
        if os.environ.get("AICODER_PROMPT_BUILD_SWITCH"):
            env_value = os.environ["AICODER_PROMPT_BUILD_SWITCH"]
            if "/" in env_value or env_value.startswith((".", "~")):
                build_source = f"File: {env_value}"
            else:
                build_source = "Environment Variable (literal)"

        imsg(f"{config.BOLD}🔧 BUILD SWITCH PROMPT")
        wmsg(f"   Source: {build_source}")
        wmsg(f"   Length: {len(build_prompt)} characters")
        print(
            f"{config.CYAN}   ──────────────────────────────────────────────────────────────{config.RESET}"
        )
        if full_mode:
            print(f"{config.WHITE}{build_prompt}{config.RESET}\n")
        else:
            print(
                f"{config.WHITE}{build_prompt[:300]}{'...' if len(build_prompt) > 300 else ''}{config.RESET}\n"
            )

        # Compaction Prompt
        compaction_prompt = get_compaction_prompt()
        compaction_source = (
            "Environment Variable"
            if os.environ.get("AICODER_PROMPT_COMPACTION")
            else "Default File"
        )
        if os.environ.get("AICODER_PROMPT_COMPACTION"):
            env_value = os.environ["AICODER_PROMPT_COMPACTION"]
            if "/" in env_value or env_value.startswith((".", "~")):
                compaction_source = f"File: {env_value}"
            else:
                compaction_source = "Environment Variable (literal)"
        else:
            # Check if we're using fallback
            if not compaction_prompt:
                compaction_source = "Hardcoded Fallback"

        imsg(f"{config.BOLD}🗜️  COMPACTION PROMPT")
        wmsg(f"   Source: {compaction_source}")
        wmsg(
            f"   Length: {len(compaction_prompt) if compaction_prompt else 0} characters"
        )
        if compaction_prompt:
            print(
                f"{config.CYAN}   ──────────────────────────────────────────────────────────────{config.RESET}"
            )
            if full_mode:
                print(f"{config.WHITE}{compaction_prompt}{config.RESET}\n")
            else:
                print(
                    f"{config.WHITE}{compaction_prompt[:300]}{'...' if len(compaction_prompt) > 300 else ''}{config.RESET}\n"
                )

        # Environment Variables Summary
        print(f"{config.BOLD}{config.MAGENTA}⚙️  ENVIRONMENT VARIABLES{config.RESET}")
        env_vars = [
            ("AICODER_PROMPT_MAIN", os.environ.get("AICODER_PROMPT_MAIN")),
            ("AICODER_PROMPT_PROJECT", os.environ.get("AICODER_PROMPT_PROJECT")),
            ("AICODER_PROMPT_PLAN", os.environ.get("AICODER_PROMPT_PLAN")),
            (
                "AICODER_PROMPT_BUILD_SWITCH",
                os.environ.get("AICODER_PROMPT_BUILD_SWITCH"),
            ),
            ("AICODER_PROMPT_COMPACTION", os.environ.get("AICODER_PROMPT_COMPACTION")),
        ]

        for var_name, var_value in env_vars:
            if var_value:
                if "/" in var_value or var_value.startswith((".", "~")):
                    wmsg(f"   {var_name}: {var_value}")
                else:
                    wmsg(f"   {var_name}: [literal content]")
            else:
                wmsg(f"   {var_name}: [not set]")

        print(f"\n{config.BOLD}{config.CYAN}{bottom_border}{config.RESET}")

        return False, False

    def _handle_prompt_list(self) -> None:
        """List available prompts from the user prompts directory."""
        from ..prompt_loader import list_available_prompts, get_user_prompts_directory

        prompts_dir = get_user_prompts_directory()
        available_prompts = list_available_prompts()

        title = "AVAILABLE PROMPTS"

        # Calculate responsive box width
        try:
            terminal_width = os.get_terminal_size().columns
            box_width = min(
                int(terminal_width * 0.8), 100
            )  # 80% of terminal width, max 100 chars
        except (OSError, AttributeError):
            box_width = 70  # Fallback width for non-terminal environments

        # Ensure minimum width based on title
        min_width = len(title) + 8  # Add padding
        box_width = max(box_width, min_width)

        top_border = "╔" + "═" * (box_width - 2) + "╗"
        bottom_border = "╚" + "═" * (box_width - 2) + "╝"

        print(f"\n{config.BOLD}{config.CYAN}{top_border}{config.RESET}")
        print(
            f"{config.BOLD}{config.CYAN}║ {title.center(box_width - 4)} ║{config.RESET}"
        )
        print(f"{config.BOLD}{config.CYAN}{bottom_border}{config.RESET}\n")

        if not available_prompts:
            wmsg(f"   No prompt files found in {prompts_dir}")
            wmsg("   Create prompt files (.txt or .md) to use this feature")
            print(f"\n{config.BOLD}{config.GREEN}Example:{config.RESET}")
            print(f"   {config.CYAN}mkdir -p {prompts_dir}{config.RESET}")
            print(
                f"   {config.CYAN}echo 'You are a Python expert' > {prompts_dir}/001-python.md{config.RESET}"
            )
            return

        print(
            f"{config.BOLD}{config.GREEN}Prompt Directory:{config.RESET} {prompts_dir}\n"
        )

        for number, filename, file_path in available_prompts:
            # Get file size for display
            try:
                file_size = file_path.stat().st_size
                size_str = f"({file_size} bytes)"
            except Exception:
                size_str = "(size unknown)"

            print(
                f"  {config.BOLD}{config.YELLOW}({number}){config.RESET} {config.WHITE}{filename}{config.RESET} {config.CYAN}{size_str}{config.RESET}"
            )

        print(f"\n{config.BOLD}{config.GREEN}Usage:{config.RESET}")
        print(
            f"  {config.YELLOW}/prompt set <number>{config.RESET}     Set prompt as active"
        )
        print(
            f"  {config.YELLOW}/prompt{config.RESET}                 Show current prompt info"
        )

    def _handle_prompt_set(self, args: List[str]) -> Tuple[bool, bool]:
        """Set a prompt from the list as the active main prompt."""
        from ..prompt_loader import list_available_prompts, load_prompt_from_file

        # Find the set command and get the number
        try:
            set_index = args.index("set")
            if set_index + 1 >= len(args):
                print(
                    f"{config.RED} *** Error: /prompt set requires a prompt number{config.RESET}"
                )
                wmsg(" *** Usage: /prompt set <number>")
                wmsg(" *** Use '/prompt list' to see available prompts")
                return False, False

            prompt_number_str = args[set_index + 1]
            try:
                prompt_number = int(prompt_number_str)
            except ValueError:
                print(
                    f"{config.RED} *** Error: '{prompt_number_str}' is not a valid number{config.RESET}"
                )
                return False, False

        except ValueError:
            print(
                f"{config.RED} *** Error: /prompt set requires a prompt number{config.RESET}"
            )
            return False, False

        # Get available prompts
        available_prompts = list_available_prompts()
        if not available_prompts:
            emsg(" *** Error: No prompt files available")
            print(
                f"{config.YELLOW} *** Use '/prompt list' to see available prompts{config.RESET}"
            )
            return False, False

        # Find the requested prompt
        selected_prompt = None
        for number, filename, file_path in available_prompts:
            if number == prompt_number:
                selected_prompt = (number, filename, file_path)
                break

        if not selected_prompt:
            emsg(f" *** Error: Prompt #{prompt_number} not found")
            wmsg(f" *** Available prompts: 1-{len(available_prompts)}")
            wmsg(" *** Use '/prompt list' to see all prompts")
            return False, False

        number, filename, file_path = selected_prompt

        import os

        # Handle special case for original prompt (#1)
        if prompt_number == 1:
            # Reset to original startup prompt (same as /prompt reset)
            if "AICODER_PROMPT_MAIN" in os.environ:
                del os.environ["AICODER_PROMPT_MAIN"]

            # Load the original prompt
            try:
                from ..prompt_loader import get_main_prompt

                prompt_content = get_main_prompt()
            except Exception:
                print(
                    f"{config.RED} *** Error: Could not load original prompt{config.RESET}"
                )
                return False, False
        else:
            # Load the prompt content from file
            prompt_content = load_prompt_from_file(file_path)
            if not prompt_content:
                print(
                    f"{config.RED} *** Error: Could not read prompt file '{filename}'{config.RESET}"
                )
                return False, False

            # Set the environment variable to override the main prompt
            os.environ["AICODER_PROMPT_MAIN"] = str(file_path)

        if prompt_number == 1:
            print(
                f"{config.GREEN} *** Successfully reset to original startup prompt{config.RESET}"
            )
        else:
            print(
                f"{config.GREEN} *** Successfully set prompt '{filename}' as active{config.RESET}"
            )
            print(
                f"{config.GREEN} *** Prompt #{number} loaded from: {file_path}{config.RESET}"
            )
        print(
            f"{config.YELLOW} *** Length: {len(prompt_content)} characters{config.RESET}"
        )
        print(
            f"\n{config.BOLD}{config.CYAN}Prompt Preview (first 200 characters):{config.RESET}"
        )
        preview = prompt_content[:200] + ("..." if len(prompt_content) > 200 else "")
        print(f"{config.WHITE}{preview}{config.RESET}")
        print(
            f"\n{config.YELLOW} *** This prompt will be used for new conversations{config.RESET}"
        )
        print(
            f"{config.YELLOW} *** Use '/prompt' to see current prompt information{config.RESET}"
        )

        # Update the system message in the current conversation
        try:
            from ..prompt_loader import get_main_prompt

            new_prompt = get_main_prompt()

            # Update the first message (system message) in the conversation
            if (
                self.app.message_history.messages
                and self.app.message_history.messages[0].get("role") == "system"
            ):
                old_prompt = self.app.message_history.messages[0]["content"]
                self.app.message_history.messages[0]["content"] = new_prompt
                print(
                    f"\n{config.GREEN} *** System prompt updated for current conversation{config.RESET}"
                )

                # Show a brief preview of what changed
                if len(old_prompt) != len(new_prompt):
                    print(
                        f"{config.YELLOW} *** Length changed from {len(old_prompt)} to {len(new_prompt)} characters{config.RESET}"
                    )
            else:
                print(
                    f"{config.YELLOW} *** Warning: Could not update current conversation - will apply to next new conversation{config.RESET}"
                )
        except Exception as e:
            print(
                f"{config.RED} *** Warning: Could not update current conversation: {e}{config.RESET}"
            )
            print(
                f"{config.YELLOW} *** New prompt will apply to next new conversation{config.RESET}"
            )

        # Return False to continue with current conversation (no need to recreate)
        return False, False

    def _handle_prompt_edit(self, args: List[str]) -> Tuple[bool, bool]:
        """Edit the current main prompt in $EDITOR."""
        import tempfile
        import subprocess

        from ..prompt_loader import get_main_prompt, get_user_prompts_directory

        # Get the current main prompt
        current_prompt = get_main_prompt()

        # Check if the current prompt is from the user prompts directory
        user_prompts_dir = get_user_prompts_directory()
        current_source = os.environ.get("AICODER_PROMPT_MAIN", "")

        edit_file_path = None
        is_user_file = False

        # If the current prompt is from a file in the user directory, edit that file directly
        if current_source and str(user_prompts_dir) in current_source:
            edit_file_path = Path(current_source)
            is_user_file = True
            print(
                f"{config.GREEN} *** Editing existing prompt file: {edit_file_path}{config.RESET}"
            )
        else:
            # Create a temporary file for editing
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, prefix="aicoder-prompt-"
            ) as tf:
                tf.write(current_prompt)
                edit_file_path = Path(tf.name)
            print(
                f"{config.GREEN} *** Creating temporary prompt file for editing: {edit_file_path}{config.RESET}"
            )
            print(
                f"{config.YELLOW} *** Note: This is not in your prompts directory. Save as ~/.config/aicoder/prompts/*.md to keep changes.{config.RESET}"
            )

        # Get the editor
        editor = os.environ.get("EDITOR", "vim")
        print(
            f"{config.YELLOW} *** Opening {editor} to edit the prompt...{config.RESET}"
        )

        try:
            # Try tmux popup first (if available and in tmux), fallback to normal editor
            if not self._run_editor_in_tmux_popup(editor, str(edit_file_path)):
                subprocess.run([editor, str(edit_file_path)], check=True)

            # Read the edited content
            with open(edit_file_path, "r", encoding="utf-8") as f:
                edited_content = f.read().strip()

            if not edited_content:
                print(
                    f"{config.RED} *** Error: Prompt file is empty after editing{config.RESET}"
                )
                if not is_user_file:
                    try:
                        edit_file_path.unlink()  # Clean up temp file
                    except FileNotFoundError:
                        pass  # File was already cleaned up
                return False, False

            # If it was a temporary file, offer to save it to the user prompts directory
            if not is_user_file:
                print(
                    f"\n{config.BOLD}{config.CYAN}Prompt edited successfully!{config.RESET}"
                )
                print(
                    f"{config.YELLOW} *** Length: {len(edited_content)} characters{config.RESET}"
                )
                print(f"\n{config.BOLD}{config.GREEN}Save options:{config.RESET}")
                print(
                    f"  {config.YELLOW}1) Save to ~/.config/aicoder/prompts/ (recommended){config.RESET}"
                )
                print(
                    f"  {config.YELLOW}2) Apply temporarily (current session only){config.RESET}"
                )
                wmsg("  3) Discard changes")

                while True:
                    try:
                        choice = input(
                            f"\n{config.CYAN}Choose option (1-3): {config.RESET}"
                        ).strip()
                        if choice == "1":
                            # Save to user prompts directory
                            user_prompts_dir.mkdir(parents=True, exist_ok=True)
                            filename = input(
                                f"{config.CYAN}Enter filename (e.g., custom-prompt.md): {config.RESET}"
                            ).strip()
                            if not filename:
                                filename = "custom-prompt.md"
                            if not (
                                filename.endswith(".txt") or filename.endswith(".md")
                            ):
                                filename += ".md"

                            save_path = user_prompts_dir / filename
                            save_path.write_text(edited_content)

                            # Set as active prompt
                            os.environ["AICODER_PROMPT_MAIN"] = str(save_path)

                            print(
                                f"{config.GREEN} *** Saved to: {save_path}{config.RESET}"
                            )
                            print(
                                f"{config.GREEN} *** Set as active prompt{config.RESET}"
                            )

                            # Update current conversation
                            self._update_conversation_prompt(edited_content)

                            # Clean up temp file
                            try:
                                try:
                                    edit_file_path.unlink()
                                except FileNotFoundError:
                                    pass
                            except FileNotFoundError:
                                pass  # File was already cleaned up or never existed
                            return False, False

                        elif choice == "2":
                            # Apply temporarily
                            os.environ["AICODER_PROMPT_MAIN"] = str(edit_file_path)
                            print(
                                f"{config.YELLOW} *** Applied temporarily for current session{config.RESET}"
                            )

                            # Update current conversation
                            self._update_conversation_prompt(edited_content)

                            # Keep temp file for the session
                            return False, False

                        elif choice == "3":
                            # Discard changes
                            print(
                                f"{config.YELLOW} *** Changes discarded{config.RESET}"
                            )
                            try:
                                edit_file_path.unlink()
                            except FileNotFoundError:
                                pass
                            return False, False

                        else:
                            print(
                                f"{config.RED} *** Invalid choice. Please enter 1, 2, or 3{config.RESET}"
                            )
                    except (EOFError, KeyboardInterrupt):
                        wmsg("\n *** Edit cancelled")
                        try:
                            edit_file_path.unlink()
                        except FileNotFoundError:
                            pass
                        return False, False
            else:
                # It was an existing user file, just update the environment and current conversation
                os.environ["AICODER_PROMPT_MAIN"] = str(edit_file_path)
                print(
                    f"{config.GREEN} *** Updated prompt file: {edit_file_path}{config.RESET}"
                )
                print(
                    f"{config.YELLOW} *** Length: {len(edited_content)} characters{config.RESET}"
                )

                # Update current conversation
                self._update_conversation_prompt(edited_content)

                return False, False

        except subprocess.CalledProcessError as e:
            print(
                f"{config.RED} *** Error: Editor failed with exit code {e.returncode}{config.RESET}"
            )
            if not is_user_file:
                try:
                    edit_file_path.unlink()  # Clean up temp file
                except FileNotFoundError:
                    pass
            return False, False
        except (KeyboardInterrupt, EOFError):
            wmsg("\n *** Edit cancelled")
            if not is_user_file:
                try:
                    edit_file_path.unlink()  # Clean up temp file
                except FileNotFoundError:
                    pass
            return False, False
        except Exception as e:
            emsg(f" *** Error during editing: {e}")
            if not is_user_file:
                try:
                    edit_file_path.unlink()  # Clean up temp file
                except FileNotFoundError:
                    pass
            return False, False

    def _handle_prompt_reset(self, args: List[str]) -> Tuple[bool, bool]:
        """Reset the main prompt to the original default."""
        import os

        # Store what we're resetting from for the message
        old_prompt_source = os.environ.get("AICODER_PROMPT_MAIN", "Default")

        # Remove the environment variable override
        if "AICODER_PROMPT_MAIN" in os.environ:
            del os.environ["AICODER_PROMPT_MAIN"]

        print(f"{config.GREEN} *** Reset main prompt to default{config.RESET}")
        print(f"{config.YELLOW} *** Previous source: {old_prompt_source}{config.RESET}")

        # Get the new default prompt
        try:
            from ..prompt_loader import get_main_prompt

            new_prompt = get_main_prompt()

            print(
                f"{config.YELLOW} *** New length: {len(new_prompt)} characters{config.RESET}"
            )

            # Show what source is being used now
            if os.environ.get("AICODER_PROMPT_MAIN"):
                new_source = os.environ["AICODER_PROMPT_MAIN"]
                if "/" in new_source or new_source.startswith((".", "~")):
                    new_source = f"File: {new_source}"
                else:
                    new_source = "Environment Variable (literal)"
            else:
                new_source = "Default File"

            print(f"{config.YELLOW} *** Current source: {new_source}{config.RESET}")

            # Update the system message in the current conversation
            if (
                self.app.message_history.messages
                and self.app.message_history.messages[0].get("role") == "system"
            ):
                old_prompt = self.app.message_history.messages[0]["content"]
                self.app.message_history.messages[0]["content"] = new_prompt
                print(
                    f"\n{config.GREEN} *** System prompt updated for current conversation{config.RESET}"
                )

                # Show a brief preview of what changed
                if len(old_prompt) != len(new_prompt):
                    print(
                        f"{config.YELLOW} *** Length changed from {len(old_prompt)} to {len(new_prompt)} characters{config.RESET}"
                    )
            else:
                print(
                    f"{config.YELLOW} *** Warning: Could not update current conversation - will apply to next new conversation{config.RESET}"
                )

        except Exception as e:
            print(
                f"{config.RED} *** Warning: Could not load default prompt: {e}{config.RESET}"
            )

        print(
            f"\n{config.YELLOW} *** Use '/prompt' to see current prompt information{config.RESET}"
        )

        # Return False to continue with current conversation
        return False, False

    def _update_conversation_prompt(self, new_prompt: str) -> None:
        """Update the system prompt in the current conversation."""
        try:
            # Update the first message (system message) in the conversation
            if (
                self.app.message_history.messages
                and self.app.message_history.messages[0].get("role") == "system"
            ):
                old_prompt = self.app.message_history.messages[0]["content"]
                self.app.message_history.messages[0]["content"] = new_prompt
                print(
                    f"\n{config.GREEN} *** System prompt updated for current conversation{config.RESET}"
                )

                # Show a brief preview of what changed
                if len(old_prompt) != len(new_prompt):
                    print(
                        f"{config.YELLOW} *** Length changed from {len(old_prompt)} to {len(new_prompt)} characters{config.RESET}"
                    )
            else:
                print(
                    f"{config.YELLOW} *** Warning: Could not update current conversation - will apply to next new conversation{config.RESET}"
                )
        except Exception as e:
            print(
                f"{config.RED} *** Warning: Could not update current conversation: {e}{config.RESET}"
            )
            print(
                f"{config.YELLOW} *** New prompt will apply to next new conversation{config.RESET}"
            )

    def _show_prompt_help(self) -> None:
        """Display help for the /prompt command."""
        print(
            f"\n{config.BOLD}{config.CYAN}╔══════════════════════════════════════════════════════════════╗{config.RESET}"
        )
        print(
            f"{config.BOLD}{config.CYAN}║                         /PROMPT HELP                         ║{config.RESET}"
        )
        print(
            f"{config.BOLD}{config.CYAN}╚══════════════════════════════════════════════════════════════╝{config.RESET}"
        )
        print()
        print(f"{config.BOLD}{config.GREEN}USAGE:{config.RESET}")
        print(
            f"  {config.YELLOW}/prompt{config.RESET}           Show current prompt (truncated)"
        )
        print(
            f"  {config.YELLOW}/prompt full{config.RESET}     Show current prompt (full content)"
        )
        print(
            f"  {config.YELLOW}/prompt list{config.RESET}     List available prompts from ~/.config/aicoder/prompts"
        )
        print(
            f"  {config.YELLOW}/prompt set <num>{config.RESET} Set prompt <num> as active main prompt"
        )
        print(
            f"  {config.YELLOW}/prompt reset{config.RESET}    Reset to original default prompt"
        )
        print(
            f"  {config.YELLOW}/prompt edit{config.RESET}      Edit current main prompt in $EDITOR"
        )
        wmsg("  /prompt help     Show this help message")
        print()
        print(f"{config.BOLD}{config.GREEN}ENVIRONMENT VARIABLES:{config.RESET}")
        print(
            f"  {config.YELLOW}AICODER_PROMPT_MAIN{config.RESET}         Override main system prompt"
        )
        print(
            f"  {config.YELLOW}AICODER_PROMPT_PROJECT{config.RESET}      Override project context file"
        )
        print(
            f"  {config.YELLOW}AICODER_PROMPT_PLAN{config.RESET}         Override planning mode prompt"
        )
        print(
            f"  {config.YELLOW}AICODER_PROMPT_BUILD_SWITCH{config.RESET} Override build switch prompt"
        )
        print(
            f"  {config.YELLOW}AICODER_PROMPT_COMPACTION{config.RESET}   Override compaction prompt"
        )
        print()
        print(f"{config.BOLD}{config.GREEN}EXAMPLES:{config.RESET}")
        wmsg("  # List available prompts")
        print("  /prompt list")
        print()
        wmsg("  # Reset to original startup prompt")
        print("  /prompt reset")
        print()
        wmsg("  # Set prompt #2 as active (user prompt)")
        print("  /prompt set 2")
        print()
        wmsg("  # Set prompt #1 as active (original startup prompt)")
        print("  /prompt set 1")
        print()
        wmsg("  # Edit current prompt in $EDITOR")
        print("  /prompt edit")
        print()
        wmsg("  # Set custom main prompt")
        print('  export AICODER_PROMPT_MAIN="You are a Go development expert"')
        print()
        wmsg("  # Use custom prompt file")
        print('  export AICODER_PROMPT_PLAN="./my-custom-plan.md"')
        print()
        wmsg("  # Change project context file")
        print('  export AICODER_PROMPT_PROJECT="CLAUDE.md"')
        print()
        print(f"{config.BOLD}{config.GREEN}PROMPT FILES:{config.RESET}")
        print(
            f"  {config.YELLOW}~/.config/aicoder/prompts/{config.RESET}  Directory for custom prompt files"
        )
        print(
            f"  {config.YELLOW}*.txt, *.md{config.RESET}                    Supported file extensions"
        )
        print(
            f"  {config.YELLOW}001-*.txt, *.md{config.RESET}                Numbered files sort first"
        )
        print()
        print(f"{config.BOLD}{config.GREEN}TEMPLATE VARIABLES:{config.RESET}")
        print(
            f"  {config.YELLOW}{{current_directory}}{config.RESET}    Current working directory"
        )
        print(
            f"  {config.YELLOW}{{current_datetime}}{config.RESET}    Current date and time"
        )
        print(
            f"  {config.YELLOW}{{system_info}}{config.RESET}         System and architecture info"
        )
        print(
            f"  {config.YELLOW}{{available_tools}}{config.RESET}     Detected system tools"
        )
        print()

    def _run_editor_in_tmux_popup(self, editor: str, file_path: str) -> bool:
        """
        Run editor in tmux popup if available and enabled, otherwise run normally.

        Args:
            editor: Editor command
            file_path: Path to the file to edit

        Returns:
            True if tmux popup was used, False otherwise
        """
        # Check if we're in tmux and popup editor is enabled
        in_tmux = os.environ.get("TMUX") is not None
        popup_enabled = getattr(config, "ENABLE_TMUX_POPUP_EDITOR", True)

        if not (in_tmux and popup_enabled):
            return False

        try:
            # Get current terminal dimensions
            try:
                terminal_width = os.get_terminal_size().columns
                terminal_height = os.get_terminal_size().lines
            except (OSError, AttributeError):
                # Fallback dimensions if terminal size detection fails
                terminal_width = 120
                terminal_height = 30

            # Calculate popup dimensions based on percentage
            width_percent = getattr(config, "TMUX_POPUP_WIDTH_PERCENT", 80)
            height_percent = getattr(config, "TMUX_POPUP_HEIGHT_PERCENT", 80)

            popup_width = max(40, int(terminal_width * width_percent / 100))
            popup_height = max(10, int(terminal_height * height_percent / 100))

            # Build tmux popup command with calculated dimensions
            popup_cmd = f'tmux display-popup -w {popup_width} -h {popup_height} -E "{editor} {file_path}"'

            if config.DEBUG:
                print(
                    f"{config.GREEN}*** Using tmux popup: {popup_width}x{popup_height} ({width_percent}% of {terminal_width}x{terminal_height}){config.RESET}"
                )

            subprocess.run(popup_cmd, shell=True, check=True)
            return True
        except Exception as e:
            if config.DEBUG:
                print(
                    f"{config.YELLOW}*** Tmux popup failed, falling back to normal editor: {e}{config.RESET}"
                )
            # Fall through to normal editor

        return False
