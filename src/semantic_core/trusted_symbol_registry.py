# ==========================================================
# TRUSTED SYMBOL REGISTRY
# ==========================================================


class TrustedSymbolRegistry:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.symbols = {

            # ==================================================
            # CRYPTO
            # ==================================================

            "bcrypt.hash": {

                "category":
                    "CRYPTO",

                "trust":
                    "HIGH",

                "description":
                    "Trusted password hashing API"
            },

            "crypto.randomBytes": {

                "category":
                    "CRYPTO",

                "trust":
                    "HIGH",

                "description":
                    "Trusted secure random generator"
            },

            # ==================================================
            # SANITIZATION
            # ==================================================

            "validator.escape": {

                "category":
                    "SANITIZER",

                "trust":
                    "HIGH",

                "description":
                    "Trusted input sanitizer"
            },

            "validator.normalizeEmail": {

                "category":
                    "SANITIZER",

                "trust":
                    "HIGH",

                "description":
                    "Trusted email sanitizer"
            },

            # ==================================================
            # AUTH
            # ==================================================

            "jwt.sign": {

                "category":
                    "AUTH",

                "trust":
                    "HIGH",

                "description":
                    "Trusted JWT signing API"
            },

            "jwt.verify": {

                "category":
                    "AUTH",

                "trust":
                    "HIGH",

                "description":
                    "Trusted JWT verification API"
            },

            # ==================================================
            # EXPRESS
            # ==================================================

            "express.Router": {

                "category":
                    "FRAMEWORK",

                "trust":
                    "HIGH",

                "description":
                    "Trusted Express router"
            }
        }

    # ======================================================
    # SYMBOL EXISTS
    # ======================================================

    def exists(

        self,

        symbol
    ):

        return symbol in self.symbols

    # ======================================================
    # GET SYMBOL
    # ======================================================

    def get(

        self,

        symbol
    ):

        return self.symbols.get(
            symbol
        )

    # ======================================================
    # IS TRUSTED
    # ======================================================

    def is_trusted(

        self,

        symbol
    ):

        if not self.exists(symbol):

            return False

        return (

            self.symbols[symbol][
                "trust"
            ]

            ==

            "HIGH"
        )

    # ======================================================
    # GET CATEGORY
    # ======================================================

    def get_category(

        self,

        symbol
    ):

        if not self.exists(symbol):

            return None

        return self.symbols[symbol][
            "category"
        ]