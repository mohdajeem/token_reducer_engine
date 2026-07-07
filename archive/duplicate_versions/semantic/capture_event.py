class CaptureEvent:

    def __init__(
        self,
        capture_name,
        text,
        file_path,
        node=None,
        function_name=None,
        metadata=None
    ):

        self.capture_name = capture_name

        self.text = text

        self.file_path = file_path

        self.node = node

        self.function_name = function_name

        self.metadata = metadata or {}

    def to_dict(self):

        return {
            "capture_name": self.capture_name,
            "text": self.text,
            "file_path": self.file_path,
            "function_name": self.function_name,
            "metadata": self.metadata
        }

    def __repr__(self):

        return (
            f"CaptureEvent("
            f"{self.capture_name}, "
            f"{self.text}, "
            f"{self.function_name})"
        )