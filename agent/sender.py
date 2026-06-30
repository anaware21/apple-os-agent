"""
sender.py — send an iMessage via AppleScript.

Public API:
    send(recipient, text)
        recipient: phone number ("+15551234567") or iCloud email
        text:      message body string
"""

import subprocess


def send(recipient: str, text: str) -> None:
    script = f"""
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{recipient}" of targetService
        send "{text}" to targetBuddy
    end tell
    """
    subprocess.run(["osascript", "-e", script], check=True)
