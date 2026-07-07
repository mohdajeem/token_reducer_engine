# ==========================================================
# INCREMENTAL GRAPH MANAGER
# ==========================================================

from incremental_runtime.snapshot_manager import (
    SnapshotManager
)

from incremental_runtime.change_detector import (
    ChangeDetector
)

from incremental_runtime.graph_invalidator import (
    GraphInvalidator
)

from impact_engine.impact_analysis import (
    ImpactAnalysis
)

class IncrementalGraphManager:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph_builder,

        match_extractor,

        project_root
    ):

        self.graph_builder = (
            graph_builder
        )

        self.match_extractor = (
            match_extractor
        )

        self.snapshot_manager = (
            SnapshotManager()
        )

        self.change_detector = (
            ChangeDetector()
        )

        self.invalidator = (
            GraphInvalidator()
        )

        self.project_root = (
            project_root
        )

    # ======================================================
    # LOAD SNAPSHOT
    # ======================================================

    def load_graph_snapshot(self):
        graph = (
            self.snapshot_manager
            .load_snapshot("latest")
        )

        if graph is None:
            return self.graph_builder.graph

        return graph

    # ======================================================
    # SAVE SNAPSHOT
    # ======================================================

    def save_graph_snapshot(

        self,

        graph
    ):

        self.snapshot_manager.save_snapshot(

            graph,

            "latest"
        )

    # ======================================================
    # DETECT CHANGED FILES
    # ======================================================

    def detect_changed_files(self):

        diff_text = (

            self.change_detector
            .get_git_diff()
        )
        print("\nRAW GIT DIFF:")
        print(diff_text)
        changes = (

            self.change_detector
            .extract_changes(
                diff_text
            )
        )

        changed_files = set()

        for change in changes:

            file_path = change.get(
                "file"
            )

            if file_path:

                changed_files.add(
                    file_path
                )

        return list(
            changed_files
        )

    # ======================================================
    # REBUILD FILE
    # ======================================================

    def rebuild_file(

        self,

        graph,

        file_path
    ):

        print("\n")
        print("=" * 80)
        print(f"♻️ REBUILDING FILE: {file_path}")
        print("=" * 80)

        # ==================================================
        # INVALIDATE OLD STATE
        # ==================================================

        graph = (

            self.invalidator
            .invalidate_file(

                graph,

                file_path
            )
        )

        # ==================================================
        # ABSOLUTE FILE PATH
        # ==================================================

        import os

        absolute_path = os.path.join(

            self.project_root,

            file_path
        )
        # ==================================================
        # EXTRACT MATCHES
        # ==================================================

        semantic_matches = (

            self.match_extractor
            .extract_file(

                self.match_extractor,

                absolute_path
            )
        )

        # ==================================================
        # REBUILD FILE SEMANTICS
        # ==================================================

        self.graph_builder.graph = (
            graph
        )

        updated_graph = (

            self.graph_builder
            .build_file(

                file_path,

                semantic_matches
            )
        )

        return updated_graph

    


    # ======================================================
    # RUN INCREMENTAL UPDATE
    # ======================================================

    # def run_incremental_update(self):
    def run_incremental_update(

        self,

        changed_files
    ):

        print("\n")
        print("=" * 80)
        print("🔥 INCREMENTAL GRAPH UPDATE")
        print("=" * 80)

        # ==================================================
        # LOAD EXISTING SNAPSHOT
        # ==================================================

        graph = (
            self.load_graph_snapshot()
        )

        print("loaded graph(inside incremental_graph_manager):", graph)

        # ==================================================
        # FIRST RUN
        # ==================================================

        snapshot_exists = (
            self.snapshot_manager
            .load_snapshot(
                "latest"
            )
            is not None
        )

        if not snapshot_exists:

            print("\nNo snapshot found")
            print("Running initial full build")

            # ==============================================
            # SAVE INITIAL SNAPSHOT
            # ==============================================

            self.save_graph_snapshot(
                graph
            )

            print("\nInitial snapshot saved")

            return graph

        # ==================================================
        # DETECT CHANGED FILES
        # ==================================================

        # changed_files = (
        #     self.detect_changed_files()
        # )

        print("\nChanged Files:")
        print(changed_files)

        # ==================================================
        # EXPAND IMPACTED FILES
        # ==================================================

        impacted_files = (
            self.find_impacted_files(
                graph,
                changed_files
            )
        )

        print("\nImpacted Files:")
        print(impacted_files)

        # ==================================================
        # NO CHANGES
        # ==================================================

        if not changed_files:

            print("\nNo changed files detected")

            return graph

        # ==================================================
        # REBUILD CHANGED FILES
        # ==================================================

        # for file_path in changed_files:
        for file_path in impacted_files:
            graph = (

                self.rebuild_file(

                    graph,

                    file_path
                )
            )

        # ==================================================
        # SAVE UPDATED SNAPSHOT
        # ==================================================

        self.save_graph_snapshot(
            graph
        )

        print("\n")
        print("=" * 80)
        print("✅ INCREMENTAL UPDATE COMPLETE")
        print("=" * 80)

        return graph
    

    # ======================================================
    # FIND IMPACTED FILES
    # ======================================================

    def find_impacted_files(self, graph, changed_files):
        impact_analysis = (ImpactAnalysis(graph))

        impacted_files = set(changed_files)

        # ==================================================
        # FIND FUNCTIONS INSIDE CHANGED FILES
        # ==================================================

        for edge in graph.get("execution_edges", []):
            if edge.get("type") != "FUNCTION_CALL":
                continue

            to_node = edge.get("to", {})

            if (to_node.get("type") == "FUNCTION"
                    and to_node.get("file") in changed_files):

                upstream = (
                    impact_analysis
                    .find_upstream_dependencies(
                        to_node.get("file"),
                        to_node.get("function")
                    )
                )

                for item in upstream:
                    from_node_upstream = item.get("from", {})

                    impacted_file = (
                        from_node_upstream.get("file")
                    )

                    if impacted_file:
                        impacted_files.add(
                            impacted_file
                        )

        return list(
            impacted_files
        )
    


    def find_changed_functions(

        self,

        graph,

        changes
    ):

        changed_functions = []

        # ==================================================
        # ITERATE CHANGES
        # ==================================================

        for change in changes:

            file_path = change.get(
                "file"
            )

            changed_lines = change.get(
                "changed_lines",
                []
            )

            if not changed_lines:
                continue

            # ==================================================
            # FIND FUNCTIONS IN FILE
            # ==================================================

            functions = (
                self.function_index.functions.get(
                    file_path,
                    {}
                )
            )

            for function_name, metadata in (
                functions.items()
            ):

                start_line = metadata.get(
                    "start_line"
                )

                end_line = metadata.get(
                    "end_line"
                )

                # ==============================================
                # LINE INSIDE FUNCTION
                # ==============================================

                for line in changed_lines:

                    if (

                        start_line
                        <=
                        line
                        <=
                        end_line
                    ):

                        changed_functions.append({

                            "file": file_path,

                            "function":
                            function_name
                        })

                        break

        return changed_functions
