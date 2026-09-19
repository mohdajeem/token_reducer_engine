import subprocess
import re
import os


class ChangeDetector:

    def __init__(self):

        pass

    # ======================================================
    # GET GIT DIFF
    # ======================================================
    
    def get_git_diff(self):

        # result = subprocess.run(

        #     [
        #         "git",
        #         "diff",
        #         "--unified=0"
        #     ],

        #     capture_output=True,

        #     text=True
        # )

        result = subprocess.run(

            [
                "git",
                "diff",
                "--unified=0"
            ],

            cwd=os.getcwd(),

            capture_output=True,

            text=True
        )

        return result.stdout

    # ======================================================
    # EXTRACT CHANGED FILES + LINES
    # ======================================================

    def extract_changes(
        self,
        diff_text
    ):

        changes = []

        current_file = None

        for line in diff_text.splitlines():

            # ==============================================
            # FILE
            # ==============================================

            if line.startswith("+++ b/"):

                current_file = (
                    line.replace(
                        "+++ b/",
                        ""
                    )
                )

            # ==============================================
            # HUNK
            # ==============================================

            elif line.startswith("@@"):

                match = re.search(

                    r"\+(\d+)(?:,(\d+))?",

                    line
                )

                if not match:
                    continue

                start_line = int(
                    match.group(1)
                )

                line_count = match.group(2)

                if line_count:
                    line_count = int(line_count)
                else:
                    line_count = 1

                changed_lines = list(

                    range(

                        start_line,

                        start_line + line_count
                    )
                )

                changes.append({

                    "file": current_file,

                    "changed_lines":
                    changed_lines
                })

        return changes

    # ======================================================
    # GET CHANGED FILES (GIT + HASH FALLBACK)
    # ======================================================

    def compute_file_hash(self, file_path):
        import hashlib
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def get_changed_files(self, repo_path):
        import json
        repo_path = os.path.abspath(repo_path)
        changed_files = set()

        cache_dir = os.path.join(repo_path, ".semantic_cache")
        os.makedirs(cache_dir, exist_ok=True)
        hash_file = os.path.join(cache_dir, "file_hashes.json")

        old_hashes = {}
        if os.path.exists(hash_file):
            try:
                with open(hash_file, "r", encoding="utf-8") as f:
                    old_hashes = json.load(f)
            except Exception:
                old_hashes = {}

        new_hashes = {}
        from language_config import IGNORE_DIRS
        ignore_dirs = IGNORE_DIRS.union({".sandbox", ".semantic_cache"})
        seen = set()
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for file in files:
                if file.endswith((".js", ".ts", ".py", ".jsx", ".tsx", ".mjs", ".cjs")):
                    abs_p = os.path.join(root, file)
                    rel_p = os.path.relpath(abs_p, repo_path).replace("\\", "/")
                    seen.add(rel_p)
                    try:
                        st = os.stat(abs_p)
                    except OSError:
                        continue
                    stamp = [int(st.st_mtime_ns), st.st_size]
                    old = old_hashes.get(rel_p)
                    # fast path: unchanged mtime+size -> unchanged (hashing every file on
                    # every call was the whole cost of a no-change check)
                    if isinstance(old, list) and len(old) == 3 and old[:2] == stamp:
                        new_hashes[rel_p] = old
                        continue
                    h = self.compute_file_hash(abs_p)
                    if h:
                        new_hashes[rel_p] = [stamp[0], stamp[1], h]
                        old_h = old[2] if isinstance(old, list) and len(old) == 3 else old
                        if old_h != h:
                            changed_files.add(rel_p)
        # deleted files
        for rel_p in old_hashes:
            if rel_p not in seen:
                changed_files.add(rel_p)

        # Save updated hashes
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                json.dump(new_hashes, f, separators=(",", ":"))
        except Exception:
            pass

        return list(changed_files)