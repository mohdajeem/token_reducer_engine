class CaptureProcessor:
    def __init__(self, graph):
        self.graph = graph
        self.handlers = {
            "import.source": self.handle_import,
            "call.func_name": self.handle_call,
            "endpoint.served_route": self.handle_route_in,
            "endpoint.called_url": self.handle_route_out,
            "db.operation": self.handle_database,
            "error.throw": self.handle_error,
            "contract.name": self.handle_contract,
        }

    def process(self, events):
        for event in events:
            handler = self.handlers.get(
                event.capture_name
            )
            if handler:
                handler(event)

    # ==========================================================
    # IMPORTS
    # ==========================================================

    def handle_import(self, event):
        self.graph.add_import(
            event.file_path,
            {
                "source": event.text,
                "function": event.function_name
            }
        )

    # ==========================================================
    # FUNCTION CALLS
    # ==========================================================

    def handle_call(self, event):
        self.graph.add_call(
            event.file_path,
            {
                "callee": event.text,
                "caller": event.function_name
            }
        )

    # ==========================================================
    # ROUTES IN
    # ==========================================================

    def handle_route_in(self, event):

        self.graph.add_route_in(
            event.file_path,
            {
                "route": event.text,
                "function": event.function_name
            }
        )

    # ==========================================================
    # ROUTES OUT
    # ==========================================================

    def handle_route_out(self, event):

        self.graph.add_route_out(
            event.file_path,
            {
                "url": event.text,
                "function": event.function_name
            }
        )

    # ==========================================================
    # DATABASE
    # ==========================================================

    def handle_database(self, event):

        self.graph.add_database(
            event.file_path,
            {
                "operation": event.text,
                "function": event.function_name
            }
        )

    # ==========================================================
    # ERRORS
    # ==========================================================

    def handle_error(self, event):

        self.graph.add_error(
            event.file_path,
            {
                "error": event.text,
                "function": event.function_name
            }
        )

    # ==========================================================
    # CONTRACTS
    # ==========================================================

    def handle_contract(self, event):

        self.graph.add_contract(
            event.file_path,
            {
                "contract": event.text,
                "function": event.function_name
            }
        )