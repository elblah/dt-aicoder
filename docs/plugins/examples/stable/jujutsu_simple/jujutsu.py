"""
This plugin replaces the input builtin so it can call jujutsu to track changes
"""

import os
import builtins
from subprocess import getstatusoutput as shell

# Configuration
ENABLED = True


def commit(msg):
    if not os.path.exists(".jj"):
        st, output = shell("jj git init")
        if st != 0:
            print("JJ could not initialize repo...", output)
            return
    st, output = shell(
        f"message=$(cat <<'EOF'\n{msg}\nEOF\n);jj commit -m \"$message\""
    )
    # print("JJ:", st, output)


if ENABLED:
    orig_input = builtins.input

    def fake_input(prompt=""):
        if ">" not in prompt:
            return
        msg = orig_input(prompt)
        commit(f"BEFORE PROMPT: {msg}")
        return msg

    builtins.input = fake_input
