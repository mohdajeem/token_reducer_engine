from collections import defaultdict

class SemanticGraph:
    def __init__(self):

        self.imports = defaultdict(list)

        self.calls = defaultdict(list)

        self.routes_in = defaultdict(list)

        self.routes_out = defaultdict(list)

        self.database = defaultdict(list)

        self.errors = defaultdict(list)

        self.contracts = defaultdict(list)

    def add_import(self, file_path, data):
        self.imports[file_path].append(data)

    def add_call(self, file_path, data):
        self.calls[file_path].append(data)

    def add_route_in(self, file_path, data):
        self.routes_in[file_path].append(data)

    def add_route_out(self, file_path, data):
        self.routes_out[file_path].append(data)

    def add_database(self, file_path, data):
        self.database[file_path].append(data)

    def add_error(self, file_path, data):
        self.errors[file_path].append(data)

    def add_contract(self, file_path, data):
        self.contracts[file_path].append(data)

    def export(self):
        return {
            "imports": dict(self.imports),
            "calls": dict(self.calls),
            "routes_in": dict(self.routes_in),
            "routes_out": dict(self.routes_out),
            "database": dict(self.database),
            "errors": dict(self.errors),
            "contracts": dict(self.contracts),
        }