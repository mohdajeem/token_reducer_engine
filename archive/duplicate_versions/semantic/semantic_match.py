class SemanticMatch:
    def __init__(self, match_type, file_path, captures, owner_function=None, scope_id="GLOBAL",start_byte=None, end_byte=None, start_point=None, end_point=None):
        self.match_type = match_type
        self.file_path = file_path
        self.captures = captures
        self.owner_function = owner_function
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