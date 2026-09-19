import json
import os

class SnapshotManager:
    def __init__(self, snapshot_dir="snapshots"):
        self.snapshot_dir = (snapshot_dir)
        # i think we should give it a absolute path
        os.makedirs(self.snapshot_dir, exist_ok=True)




    # ======================================================
    # SAVE GRAPH SNAPSHOT
    # ======================================================

    def save_snapshot(self, graph, snapshot_name="latest"):

        path = os.path.join(
            self.snapshot_dir,
            f"{snapshot_name}.json"
        )

        # compact: indent=2 made a 14.5 MB Chart.js snapshot take 1.9 s to write, on every
        # incremental update. json.dumps (one-shot C encoder) instead of json.dump (pure-Python
        # chunked encoder) is another ~4x. Write to a temp file and rename so a crash mid-write
        # never leaves a truncated snapshot behind.
        data = json.dumps(graph, separators=(",", ":"), ensure_ascii=False)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)

    # ======================================================
    # LOAD SNAPSHOT
    # ======================================================

    def load_snapshot(self, snapshot_name="latest"):
        path = os.path.join(
            self.snapshot_dir,
            f"{snapshot_name}.json"
        )

        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
        

