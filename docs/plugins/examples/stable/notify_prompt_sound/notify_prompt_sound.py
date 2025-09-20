"""
This plugin replaces the input builtin so it can monitor prompts
and notify the user about new prompt by TTS

It works well on TMUX because it only notify it the current pane
is not visible
"""

import os
import builtins
import threading
from subprocess import getstatusoutput as shell

# Configuration
ENABLED = True
NOTIFY_ONLY_IF_TMUX_PANE_IS_NOT_VISIBLE = True
PREFER_SINK = "hdmi"
ALTERNATIVE_SINK = "pipewire/combined"
TTS_PROMPT = "prompt available"
TTS_APPROVAL_AVAILABLE = "approval available"

if ENABLED:
    st, sink = shell(
        f"pactl list sinks short 2> /dev/null | grep {PREFER_SINK} | awk '{{print $2}}'"
    )
    if not sink:
        sink = ALTERNATIVE_SINK

    orig_input = builtins.input

    tmux_pane = os.environ.get("TMUX_PANE", "")

    def fake_input(prompt=""):
        if NOTIFY_ONLY_IF_TMUX_PANE_IS_NOT_VISIBLE and tmux_pane:
            st, outp = shell(
                f"""tmux display -p -t "{tmux_pane}" '#{{window_active}}'"""
            )
            if st == 0 and outp == "1":
                return orig_input(prompt)

        def say(msg):
            def fn():
                os.system(f"PULSE_SINK='{sink}' espeak '{msg}' 2> /dev/null")

            t = threading.Thread(target=fn)
            t.start()

        if ">" in prompt:
            say(TTS_PROMPT)
        elif "Choose" in prompt:
            say(TTS_APPROVAL_AVAILABLE)
        return orig_input(prompt)

    builtins.input = fake_input
