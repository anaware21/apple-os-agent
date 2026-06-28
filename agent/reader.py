"""
chat.db reader — event-driven watch over new inbound iMessages.

Watches ~/Library/Messages with FSEvents (via watchdog); on each WAL write it
runs a ROWID query for new messages. A slow poll runs alongside as a backstop
so nothing is missed if an FS event is ever coalesced or dropped.

Public API:
    watch(on_message, *, include_from_me=False)
        Blocks forever, calling on_message(msg) for each new message, where msg
        is a dict: {rowid, from_me, sender, text, time}.
"""

import sqlite3
import time
import threading
import watchdog
from pathlib import Path

DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"
MESSAGES_DIR = DB_PATH.parent

APPLE_EPOCH = 978307200          # seconds from 1970-01-01 to 2001-01-01 UTC
POLL_BACKSTOP_SECONDS = 15       # safety net if an FS event is missed
DEBOUNCE_SECONDS = 0.25          # collapse bursts of writes into one query


def _connect_ro() -> sqlite3.Connection:
    # Read-only so we never risk writing the system DB. Sees committed WAL
    # writes as long as Messages.app is running. check_same_thread=False because
    # _drain() is called from both timer threads and the main poll loop.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True,
                           timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def decode_attributed_body(blob) -> str | None:
    """
    Best-effort plain-text extraction from attributedBody (a serialized
    NSAttributedString / typedstream). Handles ordinary text messages; messages
    with mentions / links / edits may decode imperfectly. To upgrade later, swap
    this body for a real typedstream parser — callers don't need to change.
    """
    if not blob:
        return None
    i = blob.find(b"NSString")
    if i == -1:
        return None
    j = blob.find(b"+", i)              # string data begins just after this marker
    if j == -1:
        return None
    p = j + 1
    if p >= len(blob):
        return None
    n = blob[p]
    p += 1
    if n == 0x81:                       # 2-byte little-endian length
        n = int.from_bytes(blob[p:p + 2], "little"); p += 2
    elif n == 0x82:                     # 4-byte little-endian length
        n = int.from_bytes(blob[p:p + 4], "little"); p += 4
    text = blob[p:p + n].decode("utf-8", errors="replace").strip()
    return text or None


def _max_rowid(conn) -> int:
    row = conn.execute("SELECT MAX(ROWID) AS m FROM message").fetchone()
    return row["m"] or 0


def _fetch_new(conn, last_rowid: int):
    cur = conn.execute(
        """
        SELECT m.ROWID           AS rowid,
               m.text            AS text,
               m.attributedBody  AS abody,
               m.is_from_me      AS from_me,
               m.date            AS adate,
               h.id              AS sender
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.ROWID > ?
        ORDER BY m.ROWID ASC
        """,
        (last_rowid,),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "rowid": r["rowid"],
            "from_me": bool(r["from_me"]),
            "sender": r["sender"],
            "text": r["text"] or decode_attributed_body(r["abody"]),
            "time": (r["adate"] / 1e9 + APPLE_EPOCH) if r["adate"] else None,
        })
    return out


def watch(on_message, *, include_from_me: bool = False):
    """Block forever, invoking on_message(msg) for each new message."""
    if not DB_PATH.exists():
        raise SystemExit(f"chat.db not found at {DB_PATH} — is Full Disk Access granted?")

    conn = _connect_ro()
    state = {"last_rowid": _max_rowid(conn)}   # start from "now"; ignore history
    lock = threading.Lock()

    def drain():
        with lock:
            for msg in _fetch_new(conn, state["last_rowid"]):
                state["last_rowid"] = max(state["last_rowid"], msg["rowid"])
                if msg["from_me"] and not include_from_me:
                    continue
                on_message(msg)

    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class _Waker(FileSystemEventHandler):
        def __init__(self):
            self._timer = None
        def _schedule(self):
            if self._timer and self._timer.is_alive():
                return                  # a drain is already pending; coalesce
            self._timer = threading.Timer(DEBOUNCE_SECONDS, drain)
            self._timer.daemon = True
            self._timer.start()
        def on_modified(self, event):
            self._schedule()
        def on_created(self, event):
            self._schedule()

    observer = Observer()
    observer.schedule(_Waker(), str(MESSAGES_DIR), recursive=False)
    observer.start()

    try:
        while True:                     # slow poll backstop
            time.sleep(POLL_BACKSTOP_SECONDS)
            drain()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        conn.close()
