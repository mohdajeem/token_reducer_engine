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

        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                graph,
                f,
                indent=2
            )

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
        

