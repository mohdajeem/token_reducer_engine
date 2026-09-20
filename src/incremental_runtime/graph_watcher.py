import os
import time
import threading
from pathlib import Path
from language_config import IGNORE_DIRS

class GraphWatcher:
    """
    Background file watcher that monitors project files for changes
    and triggers incremental updates to the semantic graph in a thread-safe manner.
    """
    def __init__(self, project_root, incremental_graph_manager, lock, interval=1.0):
        self.project_root = Path(project_root).resolve()
        self.manager = incremental_graph_manager
        self.lock = lock
        self.interval = interval
        self.running = False
        self.thread = None
        self.file_mtimes = {}

    def _should_watch(self, file_path):
        # Check extensions
        if file_path.suffix not in (".js", ".jsx", ".py"):
            return False
        
        # Check ignore directories
        for part in file_path.parts:
            if part in IGNORE_DIRS:
                return False
        return True

    def scan_files(self):
        """Scans the project directory and returns a dict mapping relative paths to modification times."""
        current_mtimes = {}
        for root, dirs, files in os.walk(self.project_root):
            # Prune directory search
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                abs_path = Path(root) / file
                if self._should_watch(abs_path):
                    try:
                        rel_path = abs_path.relative_to(self.project_root).as_posix()
                        current_mtimes[rel_path] = abs_path.stat().st_mtime
                    except Exception:
                        pass
        return current_mtimes

    def start(self):
        """Starts the background watcher thread."""
        if self.running:
            return
        self.running = True
        self.file_mtimes = self.scan_files()
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the background watcher thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _watch_loop(self):
        while self.running:
            time.sleep(self.interval)
            try:
                current_mtimes = self.scan_files()
                changed_files = []
                
                # Detect modifications and additions
                for rel_path, mtime in current_mtimes.items():
                    if rel_path not in self.file_mtimes or mtime > self.file_mtimes[rel_path]:
                        changed_files.append(rel_path)
                
                # Detect deletions
                for rel_path in list(self.file_mtimes.keys()):
                    if rel_path not in current_mtimes:
                        changed_files.append(rel_path)

                if changed_files:
                    print(f"[Watcher] Detected changes in: {changed_files}")
                    with self.lock:
                        # Perform incremental update
                        # This updates the manager's internal graph representation and updates the snapshot
                        updated_graph = self.manager.run_incremental_update(changed_files)
                        # Sync manager's graph state back to the builder
                        self.manager.graph_builder.graph = updated_graph
                    
                    # Update local modification timestamps
                    self.file_mtimes = current_mtimes
            except Exception as e:
                import traceback
                print(f"[Watcher Error] Error during scan or update: {e}")
                traceback.print_exc()

