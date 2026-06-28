"""
Configuration template.

SETUP:
    cp config.example.py config.py
    # then edit config.py with your real values

config.py is gitignored — your API key, Apple ID, and number never get committed.
This file (config.example.py) holds only placeholders and IS committed, so the
next person (or future you) knows what to fill in.
"""

# ----------------------------------------------------------------------------
# Anthropic API  (used from Phase 4 onward; safe to leave as placeholder now)
# ----------------------------------------------------------------------------
ANTHROPIC_API_KEY = "sk-ant-REPLACE_ME"
ANTHROPIC_MODEL = "claude-sonnet-4-6"   # check docs.claude.com for current model strings

# ----------------------------------------------------------------------------
# Access control — who the agent will listen to
# ----------------------------------------------------------------------------
# Only act on messages from these senders (phone numbers like "+15551234567"
# or emails). STRONGLY recommended: leaving this empty means "accept from
# anyone," which on a public number invites spam and abuse.
ALLOWED_SENDERS = [
    # "+15551234567",
    # "you@icloud.com",
]

# Optional command prefix. If set, the agent only reacts to messages that start
# with it (e.g. "/ask what's on my calendar"). Set to None to consider every
# message. A prefix is safer and cheaper — it ignores ordinary conversation.
COMMAND_PREFIX = "/ask"

# ----------------------------------------------------------------------------
# Routing (used from Phase 3 onward)
# ----------------------------------------------------------------------------
# Cosine-similarity cutoff: messages whose best task match scores below this are
# treated as conversation and ignored. Tune once the router exists.
ROUTER_THRESHOLD = 0.45
