from collections import deque


class TaintTraversalEngine:
    """
    Security static analysis engine that propagates taint sources across inter-procedural 
    execution flows and variables to detect vulnerabilities at sensitive database sinks.
    """

    def __init__(self, graph):
        """
        Initializes the taint traversal engine with the compiled semantic graph references.
        
        Args:
            graph (Dict): The queryable semantic graph constructed by GraphBuilder.
        """

        self.graph = graph

        self.execution_edges = (
            graph.get(
                "execution_edges",
                []
            )
        )

        self.taint_sources = (
            graph.get(
                "taint_sources",
                []
            )
        )

        self.security_sinks = (
            graph.get(
                "security_sinks",
                []
            )
        )

        print("inside init of taintTraversalEngine(taint_sources):", self.taint_sources)
        print("inside init of taintTraversalEngine(security_sinks):", self.security_sinks)

    # ======================================================
    # MAIN ANALYSIS
    # ======================================================

    def analyze(self):

        findings = []
        print("inside analyze of taintTraversalEngine(taint_sources): ", self.taint_sources)

        for source in self.taint_sources:
            print("source: ",source)

            # now the problem is in this 
            source_findings = (
                self.trace_source(source)
            )

            print("source_findings:",source_findings)

            findings.extend(
                source_findings
            )

        return findings

    # ======================================================
    # TRACE SINGLE SOURCE
    # ======================================================

    def trace_source(self, source):

        findings = []
        print("="*40)
        print("inside trace_source:", source)

        start_node = {

            "type": "FUNCTION",

            "file":
            source.get("file"),

            "function":
            source.get("target_function")
        }
        print("start_node:", start_node)

        reachable = (
            self.find_reachable_functions(
                start_node
            )
        )
        print("reachable:", reachable)

        for function_node in reachable:

            sink_matches = (
                self.find_sinks_in_function(
                    function_node
                )
            )

            for sink in sink_matches:

                findings.append({

                    "type":
                    "TAINT_FLOW",

                    "severity":
                    "HIGH",

                    "source":
                    source,

                    "sink":
                    sink,

                    "reachable_function":
                    function_node
                })
        print("="*40)

        return findings

    # ======================================================
    # FIND REACHABLE FUNCTIONS
    # ======================================================

    def find_reachable_functions(

        self,

        start_node
    ):

        visited = set()

        queue = deque()

        results = []

        queue.append(start_node)

        while queue:

            current = queue.popleft()

            current_key = str(current)

            if current_key in visited:
                continue

            visited.add(current_key)

            results.append(current)

            for edge in self.execution_edges:

                if edge.get("type") != "FUNCTION_CALL":
                    continue

                from_node = edge.get(
                    "from",
                    {}
                )

                to_node = edge.get(
                    "to",
                    {}
                )

                if self.node_equals(
                    from_node,
                    current
                ):

                    queue.append(to_node)

        return results

    # ======================================================
    # FIND SINKS IN FUNCTION
    # ======================================================

    def find_sinks_in_function(

        self,

        function_node
    ):

        matches = []

        for sink in self.security_sinks:
            print("\nCHECKING SINK")
            print("SINK:", sink)
            print("FUNCTION NODE:", function_node)

            if (

                sink.get("file")
                ==
                function_node.get("file")

                and

                sink.get("target_function")
                ==
                function_node.get("function")
            ):

                matches.append(sink)

        return matches

    # ======================================================
    # NODE COMPARISON
    # ======================================================

    def node_equals(

        self,

        node1,

        node2
    ):

        return (

            node1.get("type")
            ==
            node2.get("type")

            and

            node1.get("file")
            ==
            node2.get("file")

            and

            node1.get("function")
            ==
            node2.get("function")
        )