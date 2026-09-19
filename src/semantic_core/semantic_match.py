class SemanticMatch:
    def __init__(self, match_type, file_path, captures, owner_function=None, owner_function_line=None, scope_id="GLOBAL",start_byte=None, end_byte=None, start_point=None, end_point=None):
        self.match_type = match_type
        import os
        self.file_path = os.path.normpath(str(file_path)).replace("\\", "/").replace("//", "/")
        self.captures = captures
        self.owner_function = owner_function
        # The start_line of the SPECIFIC function occurrence owner_function was
        # resolved to (via byte-range containment in match_extractor_fixed.py). Two
        # same-named methods in different classes have different byte ranges but the
        # SAME owner_function string once resolved -- this field is what lets an edge
        # built from this match be traced back to which occurrence actually made the
        # call, instead of collapsing to an ambiguous bare name.
        self.owner_function_line = owner_function_line
        # Class that owns the function this match sits in (JS: `class X {}` body, `X.prototype.fn =`,
        # `Object.assign(X.prototype, {...})`); None at module level. Set by the match extractor.
        self.owner_class = None
        # True when the file lives in a test directory / has a test suffix. Set by build_graph.
        self.is_test = False
        self.scope_id = scope_id
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.start_point = start_point
        self.end_point = end_point

    def get(self, key):
        return self.captures.get(key)

    def to_dict(self):
        return {
            "match_type": self.match_type,
            "file_path": self.file_path,
            "captures": self.captures
        }

    def __repr__(self):
        return (
            f"SemanticMatch("
            f"{self.match_type}, "
            f"{self.captures})"
        )