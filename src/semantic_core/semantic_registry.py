# from config.debug_flags import *
from config.settings import *

class SemanticRegistry:

    def __init__(self):

        self.all_matches = []

    # ======================================================
    # ADD MATCHES
    # ======================================================

    def add_matches(self, matches):
        if DEBUG_MATCHES:
            print(
                "\nADDING MATCHES:",
                len(matches)
            )

        self.all_matches.extend(
            matches
        )
        if DEBUG_MATCHES:
            print(
                "TOTAL MATCHES:",
                len(self.all_matches)
            )

    # ======================================================
    # GET MATCHES BY TYPE
    # ======================================================

    def get_matches_by_type(
        self,
        match_type
    ):

        return [

            m for m in self.all_matches

            if m.match_type == match_type
        ]