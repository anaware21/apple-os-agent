# iMessage Agent

A local agent that reads incoming iMessages on a dedicated Mac, routes them,
and replies — built to run unattended as a single-purpose appliance.

## Setup (on the appliance)

```bash
# 1. Clone (or pull) the repo
git clone <your-repo-url> imessage-agent
cd imessage-agent

# 2. Create the virtual environment and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create your local config from the template
cp config.example.py config.py
#    then edit config.py with your real values (API key, allowed senders)

# 4. Run
python3 main.py
```

### Required macOS permissions
Grant these to whatever **runs** the agent (Terminal during development, or the
Python binary / LaunchAgent later) — not to the script file:

- **Full Disk Access** — to read `~/Library/Messages/chat.db`
  (System Settings → Privacy & Security → Full Disk Access)
- **Automation → Messages** — to send replies (Phase 2+); prompted on first send

Messages.app must be signed in to the appliance Apple ID and left running.

## Secrets — important

`config.py` holds your Anthropic API key and Apple ID details and is
**gitignored**. It never gets committed. The committed template is
`config.example.py` (placeholders only). If you ever see `config.py` show up in
`git status`, stop and check `.gitignore`.

## Project structure

```
imessage-agent/
├── main.py              # entry point: load config, filter, run the loop
├── config.example.py    # committed template (no secrets)
├── config.py            # YOUR secrets — gitignored, created locally
├── requirements.txt
├── .gitignore
└── agent/
    ├── reader.py        # Phase 1: event-driven chat.db read loop  ✅
    ├── sender.py        # Phase 2: AppleScript send                (stub)
    ├── registry.py      # Phase 3: tool registry                   (later)
    └── router.py        # Phase 3: embedding dispatcher            (later)
```
