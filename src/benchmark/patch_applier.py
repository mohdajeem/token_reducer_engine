import os
import re

class PatchApplier:
    """
    Parses and applies patches (Unified Diffs or Search/Replace Blocks)
    to physical files in a target directory.
    """
    @staticmethod
    def apply_patch(repo_path: str, raw_response: str) -> dict:
        """
        Parses raw model response for patch blocks and applies them to the repo.
        Returns a dictionary with:
            - success: bool
            - applied_files: list of relative paths
            - error: str (if failed)
        """
        # Clean up code fence wrappers if present
        raw_response = PatchApplier._clean_response(raw_response)
        
        # 1. Check for SEARCH/REPLACE blocks first (often more explicit)
        search_replace_blocks = PatchApplier._parse_search_replace(raw_response)
        if search_replace_blocks:
            return PatchApplier._apply_search_replace(repo_path, search_replace_blocks)
            
        # 2. Check for Unified Diff blocks
        diff_hunks = PatchApplier._parse_unified_diff(raw_response)
        if diff_hunks:
            return PatchApplier._apply_unified_diff(repo_path, diff_hunks)
            
        # 3. Fallback: Check if there's a simple search-replace in the text
        return {
            "success": False,
            "applied_files": [],
            "error": "No recognizable patch structure (Unified Diff or Search/Replace block) found in the model response."
        }

    @staticmethod
    def _clean_response(text: str) -> str:
        """Removes outermost code block wraps if present."""
        text = text.strip()
        if text.startswith("```"):
            # strip first line
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    @staticmethod
    def _parse_search_replace(text: str) -> list:
        """
        Parses SEARCH/REPLACE blocks:
        <<<<<<< SEARCH
        original code
        =======
        replacement code
        >>>>>>> REPLACE
        
        Also tries to extract the filename from preceding text, e.g. "File: api.js"
        """
        blocks = []
        pattern = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.DOTALL)
        
        # We need to associate each block with a filename.
        # We can look for keywords like "File: filename" or "In filename:" in the preceding text.
        matches = list(pattern.finditer(text))
        
        for idx, match in enumerate(matches):
            search_content = match.group(1)
            replace_content = match.group(2)
            
            # Find filename by looking backwards from the match start
            preceding_text = text[:match.start()]
            filename = PatchApplier._infer_filename(preceding_text)
            
            blocks.append({
                "file": filename,
                "search": search_content,
                "replace": replace_content
            })
            
        return blocks

    @staticmethod
    def _infer_filename(preceding_text: str) -> str:
        """Attempts to infer the filename being modified from the preceding text."""
        lines = preceding_text.splitlines()
        # Look at the last 10 lines for filenames
        for line in reversed(lines[-10:]):
            # Check for patterns like:
            # - File: src/api.js
            # - In src/api.js:
            # - --- src/api.js
            match = re.search(r"(?:file|in|path|modify|---|\+\+\+)\s*[:\-\s]*([a-zA-Z0-9_\-\.\/\\:]+\.[a-zA-Z0-9_]+)", line, re.IGNORECASE)
            if match:
                # Return normalized path
                return match.group(1).strip().replace("\\", "/")
        return ""

    @staticmethod
    def _apply_search_replace(repo_path: str, blocks: list) -> dict:
        applied = []
        for block in blocks:
            filename = block["file"]
            if not filename:
                # If filename could not be inferred, try to match search block uniquely in the repo (fallback)
                filename = PatchApplier._find_file_with_content(repo_path, block["search"])
                if not filename:
                    return {
                        "success": False,
                        "applied_files": [],
                        "error": "Could not identify target file for Search/Replace block."
                    }
                    
            abs_path = os.path.normpath(os.path.join(repo_path, filename))
            if not os.path.exists(abs_path):
                # Try matching by basename
                inferred = PatchApplier._find_file_by_basename(repo_path, filename)
                if inferred:
                    abs_path = os.path.normpath(os.path.join(repo_path, inferred))
                    filename = inferred
                else:
                    return {
                        "success": False,
                        "applied_files": [],
                        "error": f"Target file '{filename}' does not exist."
                    }
                    
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            search_str = block["search"]
            if search_str not in content:
                # Try with normalized line endings / spaces
                norm_search = "\n".join([line.strip() for line in search_str.splitlines() if line.strip()])
                # Find matching block in content
                content_lines = content.splitlines()
                matched = False
                for i in range(len(content_lines) - len(search_str.splitlines()) + 1):
                    sub_lines = [line.strip() for line in content_lines[i:i+len(search_str.splitlines())] if line.strip()]
                    if "\n".join(sub_lines) == norm_search:
                        # Found match! Do line replacement
                        content_lines[i:i+len(search_str.splitlines())] = block["replace"].splitlines()
                        content = "\n".join(content_lines)
                        matched = True
                        break
                if not matched:
                    return {
                        "success": False,
                        "applied_files": [],
                        "error": f"Search block not found in file '{filename}'."
                    }
            else:
                content = content.replace(search_str, block["replace"])
                
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            if filename not in applied:
                applied.append(filename)
                
        return {"success": True, "applied_files": applied, "error": None}

    @staticmethod
    def _parse_unified_diff(text: str) -> list:
        """
        Parses simple unified diffs.
        Looks for hunk headers starting with @@ and applies simple line replacements.
        """
        hunks = []
        current_file = None
        current_hunk = None
        
        lines = text.splitlines()
        for line in lines:
            if line.startswith("--- "):
                # Extract old filename (usually ignored, but helps if +++ is missing)
                pass
            elif line.startswith("+++ "):
                # Extract filename
                fn_match = re.match(r"\+\+\+\s+([a-zA-Z0-9_\-\.\/\\:]+)", line)
                if fn_match:
                    current_file = fn_match.group(1).strip().replace("b/", "").replace("a/", "")
                    # Strip leading directory names if it matches standard patterns like a/ or b/
                    current_file = re.sub(r"^[ab]/", "", current_file)
            elif line.startswith("@@"):
                if current_file:
                    if current_hunk:
                        hunks.append(current_hunk)
                    current_hunk = {
                        "file": current_file,
                        "search_lines": [],
                        "replace_lines": []
                    }
            elif current_hunk:
                if line.startswith("-"):
                    current_hunk["search_lines"].append(line[1:])
                elif line.startswith("+"):
                    current_hunk["replace_lines"].append(line[1:])
                elif line.startswith(" "):
                    current_hunk["search_lines"].append(line[1:])
                    current_hunk["replace_lines"].append(line[1:])
                else:
                    # End of hunk or text
                    hunks.append(current_hunk)
                    current_hunk = None
                    
        if current_hunk:
            hunks.append(current_hunk)
            
        return hunks

    @staticmethod
    def _apply_unified_diff(repo_path: str, hunks: list) -> dict:
        applied = []
        
        # Group hunks by file
        files_hunks = {}
        for hunk in hunks:
            f = hunk["file"]
            if f not in files_hunks:
                files_hunks[f] = []
            files_hunks[f].append(hunk)
            
        for filename, f_hunks in files_hunks.items():
            abs_path = os.path.normpath(os.path.join(repo_path, filename))
            if not os.path.exists(abs_path):
                # Try matching by basename
                inferred = PatchApplier._find_file_by_basename(repo_path, filename)
                if inferred:
                    abs_path = os.path.normpath(os.path.join(repo_path, inferred))
                    filename = inferred
                else:
                    return {
                        "success": False,
                        "applied_files": [],
                        "error": f"Target file '{filename}' does not exist."
                    }
                    
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            for hunk in f_hunks:
                search_str = "\n".join(hunk["search_lines"])
                replace_str = "\n".join(hunk["replace_lines"])
                
                if search_str in content:
                    content = content.replace(search_str, replace_str)
                else:
                    # Try a line-by-line fallback
                    # Check if all search lines exist in order
                    content_lines = content.splitlines()
                    search_lines = hunk["search_lines"]
                    
                    matched = False
                    for i in range(len(content_lines) - len(search_lines) + 1):
                        slice_match = True
                        for j in range(len(search_lines)):
                            if content_lines[i+j].strip() != search_lines[j].strip():
                                slice_match = False
                                break
                        if slice_match:
                            content_lines[i:i+len(search_lines)] = hunk["replace_lines"]
                            content = "\n".join(content_lines)
                            matched = True
                            break
                            
                    if not matched:
                        return {
                            "success": False,
                            "applied_files": [],
                            "error": f"Hunk search block not found in file '{filename}'."
                        }
                        
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            if filename not in applied:
                applied.append(filename)
                
        return {"success": True, "applied_files": applied, "error": None}

    @staticmethod
    def _find_file_with_content(repo_path: str, search_content: str) -> str:
        """Finds a file in the repo containing the search block (if unique)."""
        if not search_content.strip():
            return ""
        matches = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith((".js", ".ts", ".py", ".json")):
                    full = os.path.join(root, file)
                    try:
                        with open(full, "r", encoding="utf-8") as f:
                            if search_content in f.read():
                                matches.append(os.path.relpath(full, repo_path).replace("\\", "/"))
                    except:
                        pass
        return matches[0] if len(matches) == 1 else ""

    @staticmethod
    def _find_file_by_basename(repo_path: str, filename: str) -> str:
        """Finds a file matching the trailing basename in the repo."""
        basename = os.path.basename(filename)
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file == basename:
                    full = os.path.join(root, file)
                    return os.path.relpath(full, repo_path).replace("\\", "/")
        return ""
