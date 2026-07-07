class GraphDiff:

    def __init__(

        self,

        old_graph,

        new_graph
    ):

        self.old_graph = (
            old_graph or {}
        )

        self.new_graph = (
            new_graph or {}
        )

    # ======================================================
    # MAIN DIFF
    # ======================================================

    def generate_diff(self):

        return {

            "new_routes":
            self.find_new_routes(),

            "removed_routes":
            self.find_removed_routes(),

            "new_db_operations":
            self.find_new_db_operations(),

            "new_execution_edges":
            self.find_new_execution_edges()
        }

    # ======================================================
    # NEW ROUTES
    # ======================================================

    def find_new_routes(self):

        old_routes = self.flatten(

            self.old_graph.get(
                "routes",
                {}
            )
        )

        new_routes = self.flatten(

            self.new_graph.get(
                "routes",
                {}
            )
        )

        return [

            route

            for route in new_routes

            if route not in old_routes
        ]

    # ======================================================
    # REMOVED ROUTES
    # ======================================================

    def find_removed_routes(self):

        old_routes = self.flatten(

            self.old_graph.get(
                "routes",
                {}
            )
        )

        new_routes = self.flatten(

            self.new_graph.get(
                "routes",
                {}
            )
        )

        return [

            route

            for route in old_routes

            if route not in new_routes
        ]

    # ======================================================
    # NEW DATABASE OPS
    # ======================================================

    def find_new_db_operations(self):

        old_db = self.flatten(

            self.old_graph.get(
                "database",
                {}
            )
        )

        new_db = self.flatten(

            self.new_graph.get(
                "database",
                {}
            )
        )

        return [

            db

            for db in new_db

            if db not in old_db
        ]

    # ======================================================
    # NEW EXECUTION EDGES
    # ======================================================

    def find_new_execution_edges(self):

        old_edges = self.old_graph.get(
            "execution_edges",
            []
        )

        new_edges = self.new_graph.get(
            "execution_edges",
            []
        )

        return [

            edge

            for edge in new_edges

            if edge not in old_edges
        ]

    # ======================================================
    # FLATTEN GRAPH SECTION
    # ======================================================

    def flatten(

        self,

        graph_section
    ):

        results = []

        for _, items in graph_section.items():

            results.extend(items)

        return results