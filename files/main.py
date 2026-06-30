#!/usr/bin/env python3
"""
iMessage agent — entry point.

Run from the project root with the venv active:
    python3 main.py

Phase 1: prints qualifying inbound messages.
Later phases replace the body of handle() with: route -> extract -> act -> reply.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

import config
from agent import reader
from agent import sender


def is_allowed(msg) -> bool:
    """Apply access control: allow-list, then optional command prefix."""
    if config.ALLOWED_SENDERS and msg["sender"] not in config.ALLOWED_SENDERS:
        return False
    if config.COMMAND_PREFIX:
        return bool(msg["text"]) and msg["text"].startswith(config.COMMAND_PREFIX)
    return True


def strip_prefix(text: str) -> str:
    if config.COMMAND_PREFIX and text.startswith(config.COMMAND_PREFIX):
        return text[len(config.COMMAND_PREFIX):].strip()
    return text


def handle(msg):
    if not is_allowed(msg):
        return
    request = strip_prefix(msg["text"] or "")
    when = time.strftime("%H:%M:%S", time.localtime(msg["time"])) if msg["time"] else "??:??:??"

    # ---- Phase 1: just print ----
    print(f"[{when}] task from {msg['sender']}: {request!r}  (rowid={msg['rowid']})", flush=True)

    # ---- Phase 2+: reply ----
    sender.send(msg["sender"], "hello")


if __name__ == "__main__":
    if config.ALLOWED_SENDERS:
        print(f"Listening for {config.COMMAND_PREFIX or '(any)'} from {config.ALLOWED_SENDERS}.", flush=True)
    else:
        print("WARNING: ALLOWED_SENDERS is empty — accepting from anyone. "
              "Add yourself in config.py before going live.", flush=True)
    print("Agent running (Phase 1: read loop). Ctrl-C to stop.", flush=True)
    reader.watch(handle)
