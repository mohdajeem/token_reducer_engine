# ==========================================================
# SETTINGS
# CENTRALIZED RUNTIME CONFIGURATION
# ==========================================================

import os

# ==========================================================
# AI PROVIDERS
# ==========================================================

AI_PROVIDER = os.getenv(

    "AI_PROVIDER",

    "groq"
)

# ==========================================================
# MODELS
# ==========================================================

GROQ_MODEL = os.getenv(

    "GROQ_MODEL",

    "llama3-70b-8192"
)

GEMINI_MODEL = os.getenv(

    "GEMINI_MODEL",

    "gemini-1.5-flash"
)

OPENAI_MODEL = os.getenv(

    "OPENAI_MODEL",

    "gpt-4o-mini"
)

# ==========================================================
# FEATURE FLAGS
# ==========================================================

ENABLE_TAINT_ANALYSIS = False

ENABLE_FIX_GENERATION = False

ENABLE_DIFF_ANALYSIS = False

ENABLE_IMPACT_ANALYSIS = False

ENABLE_PATCH_VALIDATION = False

# ==========================================================
# DEBUG FLAGS
# ==========================================================

DEBUG_GRAPH_BUILD = False

DEBUG_FUNCTION_SPANS = False

DEBUG_MATCHES = False

DEBUG_FUNCTION_INDEX = False

DEBUG_SYMBOL_TABLE = False

DEBUG_CALL_RESOLUTION = False

DEBUG_CHANGE_ANALYZER = False

DEBUG_IMPACT_ANALYSIS = False

DEBUG_IMPACT_ENGINE = False

DEBUG_CONTEXT_EXTRACTION = False

DEBUG_FIX_GENERATION = False

# ==========================================================
# CONTEXT LIMITS
# ==========================================================

MAX_CONTEXT_FUNCTIONS = 10

MAX_CODE_LINES = 300

MAX_DIFF_LINES = 100

# ==========================================================
# SECURITY
# ==========================================================

SECURITY_SEVERITIES = {

    "CRITICAL",

    "HIGH"
}

# ==========================================================
# PATCH GENERATION
# ==========================================================

MAX_PATCHES = 5