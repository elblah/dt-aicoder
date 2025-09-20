"""
This plugin prevent too many lines being printed in messages.
Sometimes AI sends many lines in the end of messages and this
plugin uses Python magic to fix the problem.
"""

import sys
import os

# Global max consecutive newlines to allow (as characters). Default 2 (i.e., allow up to one empty line).
_MAX_CONSEC_NL = int(os.environ.get("IGNORE_MAX_CONSEC_NL", "2"))

# Simple wrappers that drop extra newlines beyond the limit


def _make_text_writer(stream, max_nl):
    class LimitedTextWriter:
        def __init__(self, s):
            self._stream = s
            self._nl_run = 0  # number of consecutive newline chars seen

        def write(self, text):
            if not text:
                return 0
            out = []
            for ch in text:
                if ch == "\n":
                    if self._nl_run < max_nl:
                        out.append(ch)
                        self._nl_run += 1
                    # else drop extra newline
                else:
                    out.append(ch)
                    self._nl_run = 0
            data = "".join(out)
            return self._stream.write(data)

        def flush(self):
            return self._stream.flush()

    return LimitedTextWriter(stream)


def _make_bytes_writer(stream, max_nl):
    class LimitedBytesWriter:
        def __init__(self, s):
            self._stream = s
            self._nl_run = 0

        def write(self, b):
            if not b:
                return 0
            out = bytearray()
            for i in range(len(b)):
                ch = b[i : i + 1]
                if ch == b"\n":
                    if self._nl_run < max_nl:
                        out.extend(ch)
                        self._nl_run += 1
                else:
                    out.extend(ch)
                    self._nl_run = 0
            return self._stream.write(bytes(out))

        def flush(self):
            return self._stream.flush()

    return LimitedBytesWriter(stream)


# Simple proxy that exposes .buffer (when available) and routes writes through wrappers
class StdoutProxy:
    def __init__(self, orig_stdout):
        self._orig = orig_stdout
        self.buffer = getattr(orig_stdout, "buffer", None)
        self._text_writer = _make_text_writer(orig_stdout, _MAX_CONSEC_NL)
        self._bin_writer = None
        if self.buffer is not None:
            self._bin_writer = _make_bytes_writer(self.buffer, _MAX_CONSEC_NL)

    def write(self, s):
        return self._text_writer.write(s)

    def flush(self):
        return self._orig.flush()


def install(max_nl=None):
    global _MAX_CONSEC_NL
    if max_nl is not None:
        _MAX_CONSEC_NL = int(max_nl)
    # Replace stdout with proxy
    platform_stdout = sys.stdout
    sys.stdout = StdoutProxy(platform_stdout)


# Auto-install on import using environment variable
install()

# Allow programmatic override by re-importing and calling install
__all__ = ["install"]
