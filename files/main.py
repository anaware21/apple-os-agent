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
from agent.router import Router

# Placeholder task registry — replaced by agent/registry.py in a later phase.
# Each task lists example phrases a user might text to invoke it. Short trigger
# stems ("remind me to") match well even when the rest of the message is words
# the router has never seen ("...take out the trash").
TASKS = {
    "calendar": [
        "what's on my calendar today",
        "do I have any meetings tomorrow",
        "when is my next event",
        "check my calendar",
        "what's my schedule",
    ],
    "reminder": [
        "remind me to call mom at 5pm",
        "set a reminder for tomorrow morning",
        "add buy groceries to my reminders",
        "remind me to",
        "set a reminder",
    ],
}

router = Router(threshold=config.ROUTER_THRESHOLD)
for task_name, examples in TASKS.items():
    router.register(task_name, examples)


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

    # ---- Phase 3: route ----
    match = router.route(request)
    if match is None:
        # Below threshold: just conversation, ignore silently.
        print(f"[{when}] no task matched from {msg['sender']}: {request!r}", flush=True)
        return
    task_name, score = match
    print(f"[{when}] task {task_name!r} ({score:.2f}) from {msg['sender']}: {request!r}  (rowid={msg['rowid']})", flush=True)

    # ---- Phase 4+: extract -> act; for now just acknowledge the routed task ----
    sender.send(msg["sender"], f"routed to task: {task_name} (score {score:.2f})")


if __name__ == "__main__":
    if config.ALLOWED_SENDERS:
        print(f"Listening for {config.COMMAND_PREFIX or '(any)'} from {config.ALLOWED_SENDERS}.", flush=True)
    else:
        print("WARNING: ALLOWED_SENDERS is empty — accepting from anyone. "
              "Add yourself in config.py before going live.", flush=True)
    print("Agent running (Phase 1: read loop). Ctrl-C to stop.", flush=True)
    reader.watch(handle)
