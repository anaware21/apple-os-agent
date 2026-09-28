"""
router.py — embedding dispatcher: match an inbound message to a task.

Vectorizes text into sparse TF-IDF vectors over word unigrams, word bigrams,
and character trigrams (pure Python — no model download, no API call), then
routes a message to the registered task whose example phrase is most
cosine-similar. Bigrams separate command stems ("remind me", "on my calendar")
from casually shared single words; trigrams keep the match tolerant of typos
and morphology ("remind"/"reminder"). IDF is computed per task, not per
example, so a task's own signature words aren't down-weighted for recurring
across its examples. To upgrade later, swap vectorize() for a real embedding
model (e.g. Voyage or sentence-transformers) — callers don't need to change.

Public API:
    Router(threshold=0.45)
        threshold: cosine cutoff; best matches scoring below it return None
                   (main.py passes config.ROUTER_THRESHOLD).
    router.register(name, examples)
        name:     task identifier handed back by route()
        examples: list of phrases a user might send to invoke the task
    router.route(text) -> (name, score) | None
        None means "no task matched" — treat the message as conversation.
    router.vectorize(text) -> dict[str, float]
        Unit-length sparse vector for text, weighted by the current IDF.
"""

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[a-z0-9']+")


def _features(text: str) -> list[str]:
    """Word unigrams + word bigrams + character trigrams of normalized text."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return []
    padded = f" {' '.join(words)} "
    return (words
            + [f"{a} {b}" for a, b in zip(words, words[1:])]
            + [padded[i:i + 3] for i in range(len(padded) - 2)])


def _dot(a: dict, b: dict) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(w * b[f] for f, w in a.items() if f in b)


class Router:
    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold
        self._examples: list[tuple[str, str]] = []   # (task name, phrase)
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []   # parallel to _examples
        self._stale = True

    def register(self, name: str, examples: list[str]) -> None:
        """Add a task with example phrases. Callable any time; vectors and IDF
        are rebuilt lazily on the next route()/vectorize()."""
        if not examples:
            raise ValueError(f"task {name!r} needs at least one example phrase")
        self._examples += [(name, phrase) for phrase in examples]
        self._stale = True

    def _rebuild(self) -> None:
        # Smoothed IDF with document = task (a feature counts once per task no
        # matter how many of that task's examples contain it). Features shared
        # across tasks ("what's", "my") count less than task-specific ones,
        # while a task's own signature words keep full weight.
        task_feats: dict[str, set] = {}
        docs = [_features(phrase) for _, phrase in self._examples]
        for (name, _), feats in zip(self._examples, docs):
            task_feats.setdefault(name, set()).update(feats)
        n = len(task_feats)
        df = Counter()
        for feats in task_feats.values():
            df.update(feats)
        self._idf = {f: math.log((1 + n) / (1 + c)) + 1 for f, c in df.items()}
        self._default_idf = math.log(1 + n) + 1      # feature seen in no task
        self._vectors = [self._vectorize(feats) for feats in docs]
        self._stale = False

    def _vectorize(self, feats: list[str]) -> dict[str, float]:
        tf = Counter(feats)
        vec = {f: c * self._idf.get(f, self._default_idf) for f, c in tf.items()}
        norm = math.sqrt(sum(w * w for w in vec.values()))
        return {f: w / norm for f, w in vec.items()} if norm else {}

    def vectorize(self, text: str) -> dict[str, float]:
        """Unit-length sparse vector for text (empty dict for empty text)."""
        if self._stale:
            self._rebuild()
        return self._vectorize(_features(text))

    def route(self, text: str) -> tuple[str, float] | None:
        """Best (task name, cosine score) for text, or None if the best score
        is below the threshold — i.e. the message is just conversation."""
        if not self._examples:
            raise RuntimeError("route() called before any task was registered")
        vec = self.vectorize(text)
        if not vec:
            return None
        best_name, best_score = None, 0.0
        for (name, _), evec in zip(self._examples, self._vectors):
            score = _dot(vec, evec)
            if score > best_score:
                best_name, best_score = name, score
        if best_name is None or best_score < self.threshold:
            return None
        return best_name, best_score
