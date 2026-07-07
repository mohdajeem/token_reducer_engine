def classify_match(capture_names):
    capture_set = set(capture_names)
    # ======================================================
    # ROUTES
    # ======================================================
    if (
        "endpoint.served_route" in capture_set
        and
        "endpoint.served_method" in capture_set
    ):
        return "ROUTE"

    # ======================================================
    # IMPORTS
    # ======================================================

    if "import.source" in capture_set:
        return "IMPORT"

    # ======================================================
    # DATABASE
    # ======================================================

    if ("db.operation" in capture_set):
        return "DATABASE"

    # ======================================================
    # NETWORK OUT
    # ======================================================

    if "endpoint.called_url" in capture_set:
        return "HTTP_CALL"

    # ======================================================
    # ERRORS
    # ======================================================

    if "error.throw" in capture_set:
        return "ERROR"

    # ======================================================
    # CONTRACTS
    # ======================================================

    if "contract.name" in capture_set:
        return "CONTRACT"

    # ======================================================
    # DESTRUCTURED SYMBOLS
    # ======================================================

    if (

        "destructure.name" in capture_set

        and

        "destructure.source" in capture_set
    ):

        return "DESTRUCTURE_ALIAS"

    # ======================================================
    # SYMBOL ALIASES
    # ======================================================

    if (

        "alias.name" in capture_set

        and

        "alias.value" in capture_set
    ):

        return "SYMBOL_ALIAS"

    # ======================================================
    # FUNCTION PARAMETERS
    # ======================================================

    if (

        "function.name" in capture_set

        and

        "param.name" in capture_set
    ):

        return "FUNCTION_PARAMS"

    # for function 
    if "function.name" in capture_set:
        return "FUNCTION_DEF"
    

    # ======================================================
    # VARIABLE ASSIGNMENTS
    # ======================================================

    if (

        "assign.variable" in capture_set

        and

        "assign.value" in capture_set
    ):

        return "VARIABLE_ASSIGNMENT"
    
    # ======================================================
    # RETURN VALUES
    # ======================================================

    if "return.value" in capture_set:

        return "RETURN_VALUE"

    # ======================================================
    # CALL ARGUMENTS
    # ======================================================

    if "arg.value" in capture_set:

        return "CALL_ARGUMENTS"
    # ======================================================
    # CALLS
    # ======================================================

    if "call.func_name" in capture_set:
        return "CALL"

    return "UNKNOWN"