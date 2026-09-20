import re

class SymbolResolver:
    """
    Helper resolver to trace variable assignments back to class instantiations,
    resolving loose types (e.g. mapping `const user = new User()` -> `User`).
    """
    @staticmethod
    def extract_instantiated_class(assignment_value: str) -> str:
        """
        Parses JS/Python instantiation values to extract the Class name.
        Examples:
          - JS: `new User()` -> `User`
          - Python: `User()` -> `User` (starts with uppercase)
        """
        if not assignment_value:
            return None
            
        # JS instantiation: new ClassName(...) / new pkg.ClassName(...)
        js_match = re.match(r"^new\s+(?:[A-Za-z_$][\w$]*\.)*([A-Za-z_$][\w$]*)", assignment_value.strip())
        if js_match:
            return js_match.group(1)
            
        # Python/Factory instantiation: ClassName(...) / module.ClassName(...) (uppercase name)
        py_match = re.match(r"^(?:[a-z_][\w]*\.)*([A-Z][A-Za-z0-9_]*)\(", assignment_value.strip())
        if py_match:
            return py_match.group(1)
            
        return None
