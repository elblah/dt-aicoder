"""
This plugin uses event hooks to monitor prompts and notify the user about new prompts by TTS.

It works well on TMUX because it only notifies if the current pane is not visible.
"""

import os
import threading
from subprocess import getstatusoutput as shell

# Configuration
ENABLED = True
NOTIFY_ONLY_IF_TMUX_PANE_IS_NOT_VISIBLE = "ALWAYS_NOTIFY" not in os.environ
PREFER_SINK = "hdmi"
ALTERNATIVE_SINK = "pipewire/combined"
TTS_PROMPT = "prompt available"
TTS_APPROVAL_AVAILABLE = "approval available"

# Inside firejail there is no /dev/null so we use another
DEV_NULL = "/dev/null"
if "container" in os.environ:
    tmp_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    DEV_NULL = f"{tmp_dir}/.notify_null"

if ENABLED:
    st, sink = shell(
        f"pactl list sinks short 2> {DEV_NULL} | grep {PREFER_SINK} | awk '{{print $2}}'"
    )
    if not sink:
        sink = ALTERNATIVE_SINK

    tmux_pane = os.environ.get("TMUX_PANE", "")

    def say(msg):
        def fn():
            os.system(f"PULSE_SINK='{sink}' espeak '{msg}' 2> {DEV_NULL}")

        t = threading.Thread(target=fn)
        t.start()

    def should_notify():
        """Check if we should notify based on TMUX pane visibility."""
        NOTIFY_ONLY_IF_TMUX_PANE_IS_NOT_VISIBLE = "ALWAYS_NOTIFY" not in os.environ
        if not NOTIFY_ONLY_IF_TMUX_PANE_IS_NOT_VISIBLE or not tmux_pane:
            return True

        if os.path.exists(".notify-prompt"):
            return True

        st, outp = shell(f"""tmux display -p -t "{tmux_pane}" '#{{window_active}}'""")
        # Notify if pane is NOT active (outp != "1") or if command failed
        return st != 0 or outp != "1"

    def on_before_user_prompt():
        """Called before user prompt is displayed."""
        if should_notify():
            say(TTS_PROMPT)

    def on_before_approval_prompt():
        """Called before approval prompt is displayed."""
        if should_notify():
            say(TTS_APPROVAL_AVAILABLE)
