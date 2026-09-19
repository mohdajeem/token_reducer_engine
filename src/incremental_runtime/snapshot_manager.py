import json
import os
import sys
import threading

# snapshot path -> the thread still writing it. Module-level because mcp_build_graph creates
# a fresh SnapshotManager per call; the pending write must be visible across calls.
_PENDING = {}
_PENDING_LOCK = threading.Lock()
# Set = background writers may run. Cleared while the server is inside a call: the chunked
# encoder is Python bytecode, and two Python threads share the GIL in 5 ms slices, so a
# writer left running would double the time of whatever the main thread is doing (the
# change-detection walk went 0.05 s -> 1.5 s). Writers only use idle time.
_RUN = threading.Event()
_RUN.set()
_PAUSE_DEPTH = 0
_PAUSE_LOCK = threading.Lock()


class writers_paused:
    """`with writers_paused(): ...` -- background snapshot writers hold between chunks
    until the block exits. Re-entrant."""
    def __enter__(self):
        global _PAUSE_DEPTH
        with _PAUSE_LOCK:
            _PAUSE_DEPTH += 1
            _RUN.clear()
        return self

    def __exit__(self, *exc):
        global _PAUSE_DEPTH
        with _PAUSE_LOCK:
            _PAUSE_DEPTH -= 1
            if _PAUSE_DEPTH <= 0:
                _PAUSE_DEPTH = 0
                _RUN.set()
        return False


def _write(path, data):
    # Write to a temp file and rename so a crash mid-write never leaves a truncated
    # snapshot behind.
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception as e:  # pragma: no cover - disk full, permissions
        print(f"Snapshot write failed for {path}: {e}", file=sys.stderr)


def _serialize_and_write(path, graph, chunked=False, cancel=None, on_done=None):
    """chunked=True streams the pure-Python encoder straight to the file. It burns ~4x the
    CPU of the one-shot C encoder, but the C encoder holds the GIL for its whole run
    (0.28 s on astropy's 27 MB), which stalls the main thread just as much as writing
    inline would. The chunked encoder yields the GIL every few ms, so on a background
    thread it really does overlap with the idle time between tool calls."""
    tmp = path + ".tmp"
    try:
        if chunked:
            enc = json.JSONEncoder(separators=(",", ":"), ensure_ascii=False)
            with open(tmp, "w", encoding="utf-8") as f:
                for chunk in enc.iterencode(graph):
                    if cancel is not None and cancel.is_set():
                        break  # a newer graph is about to be written; this one is stale
                    if not _RUN.is_set():
                        while not _RUN.wait(0.05):  # the server is busy: give it the GIL
                            if cancel is not None and cancel.is_set():
                                break
                        if cancel is not None and cancel.is_set():
                            break
                    f.write(chunk)
            if cancel is not None and cancel.is_set():
                os.remove(tmp)
                return
            os.replace(tmp, path)
        else:
            _write(path, json.dumps(graph, separators=(",", ":"), ensure_ascii=False))
        if on_done is not None:
            on_done()  # e.g. commit the file hashes that describe this snapshot
    except Exception as e:  # mutated mid-serialization = a caller forgot wait(); disk full
        print(f"Snapshot write failed for {path}: {e}", file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass


class SnapshotManager:
    def __init__(self, snapshot_dir="snapshots"):
        self.snapshot_dir = (snapshot_dir)
        # i think we should give it a absolute path
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _path(self, snapshot_name):
        return os.path.join(self.snapshot_dir, f"{snapshot_name}.json")

    # ======================================================
    # SAVE GRAPH SNAPSHOT
    # ======================================================

    def save_snapshot(self, graph, snapshot_name="latest", background=False, on_done=None):
        """Persist `graph`. compact: indent=2 made a 14.5 MB Chart.js snapshot take 1.9 s to
        write, on every incremental update. json.dumps (one-shot C encoder) instead of
        json.dump (pure-Python chunked encoder) is another ~4x.

        background=True returns immediately and serializes + writes on a thread, so the
        cost overlaps with the model's thinking time between tool calls instead of being
        paid inside the call. The caller must not MUTATE `graph` until wait() -- reads are
        fine -- and mcp_build_graph does call wait() before every update. Writes to the
        same path are serialized in order; load/has_snapshot wait for a pending write."""
        path = self._path(snapshot_name)
        self.wait(snapshot_name, cancel=True)  # whatever is in flight is older than `graph`
        if not background:
            _serialize_and_write(path, graph, on_done=on_done)
            return
        cancel = threading.Event()
        t = threading.Thread(target=_serialize_and_write, args=(path, graph, True, cancel, on_done),
                             name="snapshot-write", daemon=False)  # non-daemon: finish on exit
        with _PENDING_LOCK:
            _PENDING[path] = (t, cancel)
        t.start()

    def wait(self, snapshot_name=None, cancel=False):
        """Block until pending background writes (for one snapshot, or all) have finished.
        cancel=True aborts them instead: the graph is about to change and a newer snapshot
        will follow, so finishing a stale one would only delay the update."""
        with _PENDING_LOCK:
            items = [(p, tc) for p, tc in _PENDING.items()
                     if snapshot_name is None or p == self._path(snapshot_name)]
        for p, (t, ev) in items:
            if cancel:
                ev.set()
            t.join()
            with _PENDING_LOCK:
                if _PENDING.get(p) is not None and _PENDING[p][0] is t:
                    del _PENDING[p]

    def writing(self, snapshot_name="latest"):
        with _PENDING_LOCK:
            tc = _PENDING.get(self._path(snapshot_name))
        return tc is not None and tc[0].is_alive()

    # ======================================================
    # LOAD SNAPSHOT
    # ======================================================

    def has_snapshot(self, snapshot_name="latest"):
        # a pending background write counts: the file is on its way. Never block here --
        # this runs on the hot path before every tool call.
        return self.writing(snapshot_name) or os.path.isfile(self._path(snapshot_name))

    def load_snapshot(self, snapshot_name="latest"):
        self.wait(snapshot_name)
        path = self._path(snapshot_name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
