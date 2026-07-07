# ==========================================================
# GRAPH INVALIDATOR TEST
# ==========================================================

from semantic.incremental.graph_invalidator import (
    GraphInvalidator
)


# ==========================================================
# RUN TEST
# ==========================================================

def run_graph_invalidator_test():

    print("\n")
    print("=" * 80)
    print("🔥 GRAPH INVALIDATOR TEST")
    print("=" * 80)

    # ======================================================
    # SAMPLE GRAPH
    # ======================================================

    graph = {

        "routes": {

            "services/userService.js": [

                {
                    "path": "/users",
                    "method": "GET"
                }
            ],

            "controllers/userController.js": [

                {
                    "path": "/login",
                    "method": "POST"
                }
            ]
        },

        "calls": {

            "services/userService.js": [

                {
                    "function": "fetchUsers"
                }
            ]
        },

        "execution_edges": [

            {
                "from": {

                    "file":
                        "services/userService.js"
                },

                "to": {

                    "file":
                        "controllers/userController.js"
                }
            },

            {
                "from": {

                    "file":
                        "controllers/userController.js"
                },

                "to": {

                    "file":
                        "db/userRepo.js"
                }
            }
        ],

        "variable_states": [

            {
                "file":
                    "services/userService.js",

                "variable":
                    "password"
            },

            {
                "file":
                    "controllers/userController.js",

                "variable":
                    "safeEmail"
            }
        ],

        "returns": [

            {
                "file":
                    "services/userService.js",

                "value":
                    "password"
            }
        ]
    }

    # ======================================================
    # INVALIDATE FILE
    # ======================================================

    invalidator = (
        GraphInvalidator()
    )

    updated_graph = (

        invalidator.invalidate_file(

            graph,

            "services/userService.js"
        )
    )

    # ======================================================
    # RESULTS
    # ======================================================

    print("\nUPDATED GRAPH:")
    print(updated_graph)

    return updated_graph