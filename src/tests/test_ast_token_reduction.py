import unittest
import os
import shutil
import tempfile
from context_engine.context_extractor import ContextExtractor

class TestASTTokenReduction(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.extractor = ContextExtractor(graph={}, project_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_extract_python_function_signature_with_docstring(self):
        # Create a dummy python file
        py_code = (
            "def helper_func(x, y):\n"
            "    \"\"\"This is a test docstring.\"\"\"\n"
            "    res = x + y\n"
            "    return res\n"
        )
        file_path = "test_file.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        sig = self.extractor.extract_function_signature(file_path, "helper_func")
        self.assertIsNotNone(sig)
        self.assertIn("def helper_func(x, y):", sig)
        self.assertIn("\"\"\"This is a test docstring.\"\"\"", sig)
        self.assertNotIn("res = x + y", sig)
        self.assertIn("# [Body pruned for token reduction]", sig)

    def test_extract_js_function_signature(self):
        js_code = (
            "function getSomething(a, b) {\n"
            "    const val = a * b;\n"
            "    return val;\n"
            "}\n"
        )
        file_path = "test_file.js"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(js_code)

        sig = self.extractor.extract_function_signature(file_path, "getSomething")
        self.assertIsNotNone(sig)
        self.assertIn("function getSomething(a, b)", sig)
        self.assertNotIn("const val = a * b;", sig)
        self.assertIn("// [Body pruned for token reduction]", sig)

    def test_extract_database_schema_class_python(self):
        py_code = (
            "import os\n\n"
            "class UserModel(db.Model):\n"
            "    id = db.Column(db.Integer, primary_key=True)\n"
            "    name = db.Column(db.String(100))\n\n"
            "class PostModel(db.Model):\n"
            "    id = db.Column(db.Integer, primary_key=True)\n"
        )
        file_path = "models.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        schema = self.extractor.extract_database_schema(file_path, "UserModel")
        self.assertIsNotNone(schema)
        self.assertIn("class UserModel(db.Model):", schema)
        self.assertIn("name = db.Column(db.String(100))", schema)
        self.assertNotIn("class PostModel(db.Model):", schema)

    def test_extract_database_schema_js(self):
        js_code = (
            "const mongoose = require('mongoose');\n"
            "const UserSchema = new mongoose.Schema({\n"
            "    username: String,\n"
            "    email: String\n"
            "});\n"
            "module.exports = mongoose.model('User', UserSchema);\n"
        )
        file_path = "models.js"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(js_code)

        schema = self.extractor.extract_database_schema(file_path, "User")
        self.assertIsNotNone(schema)
        self.assertIn("const UserSchema = new mongoose.Schema", schema)
        self.assertIn("username: String", schema)

    def test_extract_python_class_method(self):
        py_code = (
            "class PreparedRequest:\n"
            "    def prepare_url(self, url, params):\n"
            "        \"\"\"Prepare URL.\"\"\"\n"
            "        self.url = url\n"
            "        return url\n"
        )
        file_path = "models.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        # Test full code extraction
        code = self.extractor.extract_function_code(file_path, "PreparedRequest.prepare_url")
        self.assertIsNotNone(code)
        self.assertIn("def prepare_url(self, url, params):", code)
        self.assertIn("self.url = url", code)

        # Test signature extraction
        sig = self.extractor.extract_function_signature(file_path, "PreparedRequest.prepare_url")
        self.assertIsNotNone(sig)
        self.assertIn("def prepare_url(self, url, params):", sig)
        self.assertNotIn("self.url = url", sig)
        self.assertIn("# [Body pruned for token reduction]", sig)

    def test_extract_js_class_method(self):
        js_code = (
            "class AuthController {\n"
            "    login(req, res) {\n"
            "        return res.send('ok');\n"
            "    }\n"
            "}\n"
        )
        file_path = "auth.js"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(js_code)

        # Test full code extraction
        code = self.extractor.extract_function_code(file_path, "AuthController.login")
        self.assertIsNotNone(code)
        self.assertIn("login(req, res)", code)
        self.assertIn("return res.send('ok');", code)

        # Test signature extraction
        sig = self.extractor.extract_function_signature(file_path, "AuthController.login")
        self.assertIsNotNone(sig)
        self.assertIn("login(req, res)", sig)
        self.assertNotIn("return res.send('ok');", sig)
        self.assertIn("// [Body pruned for token reduction]", sig)

    def test_extract_call_sites(self):
        py_code = (
            "def main_func():\n"
            "    x = 10\n"
            "    res = helper_func(x, 20)\n"
            "    print(res)\n"
            "    return helper_func(5, 5)\n"
        )
        file_path = "calls.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        calls = self.extractor.extract_call_sites(file_path, "main_func", "helper_func")
        self.assertEqual(len(calls), 2)
        self.assertTrue(any("res = helper_func(x, 20)" in c for c in calls))
        self.assertTrue(any("return helper_func(5, 5)" in c for c in calls))

    def test_extract_class_constructor(self):
        py_code = (
            "class MyClass:\n"
            "    def __init__(self, val):\n"
            "        self.val = val\n"
            "    def get_val(self):\n"
            "        return self.val\n"
        )
        file_path = "cls.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        constructor = self.extractor.extract_class_constructor(file_path, "MyClass")
        self.assertIsNotNone(constructor)
        self.assertIn("def __init__(self, val):", constructor)
        self.assertIn("self.val = val", constructor)
        self.assertNotIn("def get_val(self):", constructor)

    def test_signature_keeps_indentation(self):
        py_code = (
            "class MyClass:\n"
            "    def my_method(self):\n"
            "        print('hello')\n"
        )
        file_path = "cls.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        sig = self.extractor.extract_function_signature(file_path, "MyClass.my_method")
        self.assertIsNotNone(sig)
        self.assertTrue(sig.startswith("    def my_method(self):"))

    def test_extract_decorated_function(self):
        py_code = (
            "@app.route('/login', methods=['POST'])\n"
            "@wraps(fn)\n"
            "def login_route():\n"
            "    return 'logged in'\n"
        )
        file_path = "routes.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        code = self.extractor.extract_function_code(file_path, "login_route")
        self.assertIsNotNone(code)
        self.assertIn("@app.route('/login', methods=['POST'])", code)
        self.assertIn("@wraps(fn)", code)
        self.assertIn("def login_route():", code)

    def test_extract_import_header(self):
        py_code = (
            "import os\n"
            "from flask import Flask, request, g\n"
            "from .utils import helper\n\n"
            "app = Flask(__name__)\n"
        )
        file_path = "app.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("import os", header)
        self.assertIn("from flask import Flask, request, g", header)
        self.assertIn("from .utils import helper", header)
        self.assertNotIn("app = Flask(__name__)", header)

    def test_find_parent_class_name(self):
        py_code = (
            "class Flask:\n"
            "    def __init__(self):\n"
            "        self.custom_domain = None\n"
            "    def open_session(self, request):\n"
            "        return None\n"
        )
        file_path = "src/flask/app.py"
        os.makedirs(os.path.join(self.temp_dir, "src/flask"), exist_ok=True)
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        parent_cls = self.extractor.find_parent_class_name(file_path, "open_session")
        self.assertEqual(parent_cls, "Flask")

        # Test context extraction includes CONSTRUCTOR Flask snippet automatically
        impact = {
            "target": {"type": "FUNCTION", "file": file_path, "function": "open_session"},
            "affected_functions": [{"file": file_path, "function": "open_session"}]
        }
        ctx = self.extractor.extract_context(impact)
        constructor_snip = next((s for s in ctx["code_snippets"] if s["function"] == "CONSTRUCTOR Flask"), None)
        self.assertIsNotNone(constructor_snip)
        self.assertIn("def __init__(self):", constructor_snip["code"])
        self.assertIn("self.custom_domain = None", constructor_snip["code"])
        # the snippet must be quotable verbatim: no marker line the file does not contain
        self.assertNotIn("AST_CONSTRUCTOR_END", constructor_snip["code"])

    def test_init_signature_unpruned(self):
        py_code = (
            "class App:\n"
            "    def __init__(self):\n"
            "        self.a = 1\n"
            "        self.b = 2\n"
        )
        file_path = "app.py"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        sig = self.extractor.extract_function_signature(file_path, "App.__init__")
        self.assertIsNotNone(sig)
        self.assertIn("self.a = 1", sig)
        self.assertIn("self.b = 2", sig)
        self.assertNotIn("# [Body pruned for token reduction]", sig)

    def test_resolve_target_node_with_dotted_spec(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from main import resolve_target_node

        mock_graph = {
            "functions": {
                "src/flask/app.py": [
                    {"name": "open_session", "start_line": 10, "end_line": 20}
                ]
            }
        }
        resolved = resolve_target_node(mock_graph, "FUNCTION:Flask.open_session")
        self.assertEqual(resolved["type"], "FUNCTION")
        self.assertEqual(resolved["file"], "src/flask/app.py")
        self.assertEqual(resolved["function"], "Flask.open_session")

    def test_dotted_target_constructor_injection(self):
        py_code = (
            "class Flask:\n"
            "    def __init__(self):\n"
            "        self.send_file_max_age_default = 3600\n"
            "    def get_send_file_max_age(self, filename):\n"
            "        return self.send_file_max_age_default\n"
        )
        file_path = "src/flask/app.py"
        os.makedirs(os.path.join(self.temp_dir, "src/flask"), exist_ok=True)
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(py_code)

        # Simulating extract_context with graph base name indexing
        self.extractor.graph = {
            "functions": {
                file_path: [
                    {"name": "get_send_file_max_age", "start_line": 4, "end_line": 5}
                ]
            }
        }
        impact = {
            "target": {"type": "FUNCTION", "file": "", "function": "Flask.get_send_file_max_age"},
            "affected_functions": [{"file": file_path, "function": "Flask.get_send_file_max_age"}]
        }
        ctx = self.extractor.extract_context(impact)
        constructor_snip = next((s for s in ctx["code_snippets"] if s["function"] == "CONSTRUCTOR Flask"), None)
        self.assertIsNotNone(constructor_snip)
        self.assertIn("def __init__(self):", constructor_snip["code"])
        self.assertIn("self.send_file_max_age_default = 3600", constructor_snip["code"])
        # the snippet must be quotable verbatim: no marker line the file does not contain
        self.assertNotIn("AST_CONSTRUCTOR_END", constructor_snip["code"])

    def test_extract_java_method_and_constructor(self):
        java_code = (
            "package com.example;\n"
            "import org.springframework.web.bind.annotation.GetMapping;\n"
            "import org.springframework.web.bind.annotation.RestController;\n\n"
            "@RestController\n"
            "public class UserController {\n"
            "    private final UserService userService;\n"
            "    public UserController(UserService userService) {\n"
            "        this.userService = userService;\n"
            "    }\n"
            "    @GetMapping(\"/users/{id}\")\n"
            "    public User getUserById(Long id) {\n"
            "        return userService.findById(id);\n"
            "    }\n"
            "}\n"
        )
        file_path = "UserController.java"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(java_code)

        # Test Java code extraction
        code = self.extractor.extract_function_code(file_path, "UserController.getUserById")
        self.assertIsNotNone(code)
        self.assertIn("public User getUserById(Long id)", code)

        # Test Java constructor extraction
        constructor = self.extractor.extract_class_constructor(file_path, "UserController")
        self.assertIsNotNone(constructor)
        self.assertIn("public UserController(UserService userService)", constructor)

        # Test Java import header extraction
        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("import org.springframework.web.bind.annotation.GetMapping;", header)

    def test_extract_java_method_with_annotations(self):
        java_code = (
            "package com.example;\n"
            "import org.springframework.web.bind.annotation.*;\n\n"
            "public class RecipientController {\n"
            "    @RequestMapping(path = \"/recipients/{name}\", method = RequestMethod.GET)\n"
            "    @PreAuthorize(\"hasRole('USER')\")\n"
            "    public Recipient getRecipientByAccountName(@PathVariable String name) {\n"
            "        return recipientService.findByAccountName(name);\n"
            "    }\n"
            "}\n"
        )
        file_path = "RecipientController.java"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(java_code)

        code = self.extractor.extract_function_code(file_path, "RecipientController.getRecipientByAccountName")
        self.assertIsNotNone(code)
        self.assertIn("@RequestMapping(path = \"/recipients/{name}\", method = RequestMethod.GET)", code)
        self.assertIn("@PreAuthorize(\"hasRole('USER')\")", code)
        self.assertIn("public Recipient getRecipientByAccountName(@PathVariable String name)", code)

        sig = self.extractor.extract_function_signature(file_path, "RecipientController.getRecipientByAccountName")
        self.assertIsNotNone(sig)
        self.assertIn("@RequestMapping(path = \"/recipients/{name}\", method = RequestMethod.GET)", sig)

    def test_extract_typescript_basic_function(self):
        ts_code = (
            "import { User } from './types';\n\n"
            "export function formatUserName(user: User, options?: { uppercase?: boolean }): string {\n"
            "    const name = `${user.firstName} ${user.lastName}`;\n"
            "    return options?.uppercase ? name.toUpperCase() : name;\n"
            "}\n"
        )
        file_path = "utils.ts"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(ts_code)

        code = self.extractor.extract_function_code(file_path, "formatUserName")
        self.assertIsNotNone(code)
        self.assertIn("user: User", code)

        sig = self.extractor.extract_function_signature(file_path, "formatUserName")
        self.assertIsNotNone(sig)
        self.assertIn("export function formatUserName", sig)
        self.assertIn("// [Body pruned for token reduction]", sig)

    def test_extract_typescript_class_method_and_constructor(self):
        ts_code = (
            "interface Config {\n"
            "    endpoint: string;\n"
            "}\n\n"
            "export class ApiService {\n"
            "    private endpoint: string;\n"
            "    constructor(config: Config) {\n"
            "        this.endpoint = config.endpoint;\n"
            "    }\n\n"
            "    public async fetchData<T>(resource: string): Promise<T> {\n"
            "        const res = await fetch(`${this.endpoint}/${resource}`);\n"
            "        return res.json();\n"
            "    }\n"
            "}\n"
        )
        file_path = "ApiService.ts"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(ts_code)

        code = self.extractor.extract_function_code(file_path, "ApiService.fetchData")
        self.assertIsNotNone(code)
        self.assertIn("public async fetchData<T>(resource: string)", code)

        constructor = self.extractor.extract_class_constructor(file_path, "ApiService")
        self.assertIsNotNone(constructor)
        self.assertIn("constructor(config: Config)", constructor)
        self.assertNotIn("AST_CONSTRUCTOR_END", constructor)

        parent = self.extractor.find_parent_class_name(file_path, "fetchData")
        self.assertEqual(parent, "ApiService")

    def test_extract_typescript_arrow_function_with_generics(self):
        ts_code = (
            "export const filterItems = <T extends object>(items: T[], predicate: (item: T) => boolean): T[] => {\n"
            "    return items.filter(predicate);\n"
            "};\n"
        )
        file_path = "helpers.ts"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(ts_code)

        code = self.extractor.extract_function_code(file_path, "filterItems")
        self.assertIsNotNone(code)
        self.assertIn("<T extends object>", code)

    def test_extract_tsx_react_component(self):
        tsx_code = (
            "import React from 'react';\n"
            "import { User } from './types';\n\n"
            "interface Props {\n"
            "    user: User;\n"
            "}\n\n"
            "export const UserCard: React.FC<Props> = ({ user }) => {\n"
            "    return (\n"
            "        <div className=\"user-card\">\n"
            "            <h3>{user.name}</h3>\n"
            "        </div>\n"
            "    );\n"
            "};\n"
        )
        file_path = "UserCard.tsx"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(tsx_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("import React from 'react';", header)

        code = self.extractor.extract_function_code(file_path, "UserCard")
        self.assertIsNotNone(code)
        self.assertIn("UserCard: React.FC<Props>", code)

    def test_extract_go_function_and_method(self):
        go_code = (
            "package main\n\n"
            "import \"fmt\"\n\n"
            "func ProcessOrder(orderID int) error {\n"
            "    fmt.Println(\"Processing\", orderID)\n"
            "    return nil\n"
            "}\n"
        )
        file_path = "main.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        code = self.extractor.extract_function_code(file_path, "ProcessOrder")
        self.assertIsNotNone(code)
        self.assertIn("func ProcessOrder(orderID int) error", code)

        sig = self.extractor.extract_function_signature(file_path, "ProcessOrder")
        self.assertIsNotNone(sig)
        self.assertIn("func ProcessOrder(orderID int) error", sig)

    def test_extract_go_struct_method_and_receiver(self):
        go_code = (
            "package controllers\n\n"
            "type OrderServer struct {\n"
            "    db string\n"
            "}\n\n"
            "func (s *OrderServer) CreateOrder(w string, r string) string {\n"
            "    return \"order_created\"\n"
            "}\n"
        )
        file_path = "order_controller.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        code = self.extractor.extract_function_code(file_path, "OrderServer.CreateOrder")
        self.assertIsNotNone(code)
        self.assertIn("func (s *OrderServer) CreateOrder", code)

        parent = self.extractor.find_parent_class_name(file_path, "CreateOrder")
        self.assertEqual(parent, "OrderServer")

    def test_extract_go_import_and_package_header(self):
        go_code = (
            "package main\n\n"
            "import (\n"
            "    \"fmt\"\n"
            "    \"net/http\"\n"
            ")\n\n"
            "func main() {\n"
            "    http.ListenAndServe(\":8080\", nil)\n"
            "}\n"
        )
        file_path = "server.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("package main", header)
        self.assertIn("import (", header)

    def test_extract_go_receiver_variations(self):
        go_code = (
            "package service\n\n"
            "type UserStore struct{}\n\n"
            "// Value receiver\n"
            "func (s UserStore) GetVal() string { return \"val\" }\n\n"
            "// Unnamed pointer receiver\n"
            "func (*UserStore) Reset() { }\n"
        )
        file_path = "user_store.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        val_code = self.extractor.extract_function_code(file_path, "UserStore.GetVal")
        self.assertIsNotNone(val_code)
        self.assertIn("func (s UserStore) GetVal()", val_code)

        reset_code = self.extractor.extract_function_code(file_path, "UserStore.Reset")
        self.assertIsNotNone(reset_code)
        self.assertIn("func (*UserStore) Reset()", reset_code)

    def test_extract_go_multiple_return_tuples(self):
        go_code = (
            "package api\n\n"
            "type User struct{}\n\n"
            "func FetchUser(id int) (User, error) {\n"
            "    return User{}, nil\n"
            "}\n\n"
            "func FetchUserNamed(id int) (u User, err error) {\n"
            "    return User{}, nil\n"
            "}\n"
        )
        file_path = "api.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        sig1 = self.extractor.extract_function_signature(file_path, "FetchUser")
        self.assertIsNotNone(sig1)
        self.assertIn("func FetchUser(id int) (User, error)", sig1)

        sig2 = self.extractor.extract_function_signature(file_path, "FetchUserNamed")
        self.assertIsNotNone(sig2)
        self.assertIn("func FetchUserNamed(id int) (u User, err error)", sig2)

    def test_extract_go_doc_comments(self):
        go_code = (
            "package utils\n\n"
            "// FormatName formats the first and last name into a single string.\n"
            "// It handles empty strings gracefully.\n"
            "func FormatName(first, last string) string {\n"
            "    return first + \" \" + last\n"
            "}\n"
        )
        file_path = "utils.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(go_code)

        code = self.extractor.extract_function_code(file_path, "FormatName")
        self.assertIsNotNone(code)
        self.assertIn("// FormatName formats the first and last name into a single string.", code)
        self.assertIn("// It handles empty strings gracefully.", code)
        self.assertIn("func FormatName(first, last string) string", code)

    def test_extract_rust_standalone_function(self):
        rust_code = (
            "pub async fn calculate_total(prices: &[f64]) -> f64 {\n"
            "    prices.iter().sum()\n"
            "}\n"
        )
        file_path = "math.rs"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(rust_code)

        code = self.extractor.extract_function_code(file_path, "calculate_total")
        self.assertIsNotNone(code)
        self.assertIn("pub async fn calculate_total", code)

        sig = self.extractor.extract_function_signature(file_path, "calculate_total")
        self.assertIsNotNone(sig)
        self.assertIn("pub async fn calculate_total(prices: &[f64]) -> f64", sig)

    def test_extract_rust_impl_method_and_parent(self):
        rust_code = (
            "pub struct UserStore {\n"
            "    db_url: String,\n"
            "}\n\n"
            "impl UserStore {\n"
            "    pub fn new(db_url: String) -> Self {\n"
            "        UserStore { db_url }\n"
            "    }\n\n"
            "    pub async fn find_by_id(&self, id: u64) -> Option<String> {\n"
            "        Some(\"user\".to_string())\n"
            "    }\n"
            "}\n"
        )
        file_path = "user_store.rs"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(rust_code)

        code = self.extractor.extract_function_code(file_path, "UserStore.find_by_id")
        self.assertIsNotNone(code)
        self.assertIn("pub async fn find_by_id(&self, id: u64)", code)

        parent = self.extractor.find_parent_class_name(file_path, "find_by_id")
        self.assertEqual(parent, "UserStore")

    def test_extract_rust_attributes(self):
        rust_code = (
            "#[get(\"/api/health\")]\n"
            "#[inline]\n"
            "pub async fn health_check() -> &'static str {\n"
            "    \"OK\"\n"
            "}\n"
        )
        file_path = "routes.rs"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(rust_code)

        code = self.extractor.extract_function_code(file_path, "health_check")
        self.assertIsNotNone(code)
        self.assertIn("#[get(\"/api/health\")]", code)
        self.assertIn("#[inline]", code)
        self.assertIn("pub async fn health_check()", code)

    def test_extract_rust_use_import_header(self):
        rust_code = (
            "use std::collections::HashMap;\n"
            "use std::sync::Arc;\n\n"
            "fn main() {}\n"
        )
        file_path = "main.rs"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(rust_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("use std::collections::HashMap;", header)
        self.assertIn("use std::sync::Arc;", header)

    def test_extract_rust_generic_and_trait_impl(self):
        rust_code = (
            "pub struct Container<T> {\n"
            "    value: T,\n"
            "}\n\n"
            "impl<T: Clone> Container<T> {\n"
            "    pub fn get_clone(&self) -> T {\n"
            "        self.value.clone()\n"
            "    }\n"
            "}\n\n"
            "impl<T: std::fmt::Display> std::fmt::Display for Container<T> {\n"
            "    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {\n"
            "        write!(f, \"Container\")\n"
            "    }\n"
            "}\n"
        )
        file_path = "container.rs"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(rust_code)

        generic_code = self.extractor.extract_function_code(file_path, "Container.get_clone")
        self.assertIsNotNone(generic_code)
        self.assertIn("pub fn get_clone(&self) -> T", generic_code)

        trait_parent = self.extractor.find_parent_class_name(file_path, "fmt")
        self.assertEqual(trait_parent, "Container")

    def test_extract_c_function(self):
        c_code = (
            "#include <stdio.h>\n\n"
            "int add(int a, int b) {\n"
            "    return a + b;\n"
            "}\n"
        )
        file_path = "math.c"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(c_code)

        code = self.extractor.extract_function_code(file_path, "add")
        self.assertIsNotNone(code)
        self.assertIn("int add(int a, int b)", code)

        sig = self.extractor.extract_function_signature(file_path, "add")
        self.assertIsNotNone(sig)
        self.assertIn("int add(int a, int b)", sig)

    def test_extract_cpp_class_method(self):
        cpp_code = (
            "#include <string>\n\n"
            "class UserStore {\n"
            "public:\n"
            "    std::string get_name(int id) {\n"
            "        return \"user\";\n"
            "    }\n"
            "};\n"
        )
        file_path = "user_store.cpp"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(cpp_code)

        code = self.extractor.extract_function_code(file_path, "UserStore.get_name")
        self.assertIsNotNone(code)
        self.assertIn("std::string get_name(int id)", code)

        parent = self.extractor.find_parent_class_name(file_path, "get_name")
        self.assertEqual(parent, "UserStore")

    def test_extract_cpp_outofclass_method(self):
        cpp_code = (
            "#include <iostream>\n\n"
            "class UserStore {\n"
            "public:\n"
            "    void save_user(int id);\n"
            "};\n\n"
            "void UserStore::save_user(int id) {\n"
            "    std::cout << \"Saving\" << id;\n"
            "}\n"
        )
        file_path = "user_store_impl.cpp"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(cpp_code)

        code = self.extractor.extract_function_code(file_path, "UserStore.save_user")
        self.assertIsNotNone(code)
        self.assertIn("void UserStore::save_user(int id)", code)

    def test_extract_c_cpp_includes(self):
        cpp_code = (
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include \"user_store.h\"\n\n"
            "int main() { return 0; }\n"
        )
        file_path = "main.cpp"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(cpp_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        self.assertIn("#include <iostream>", header)
        self.assertIn("#include \"user_store.h\"", header)

    def test_small_file_bypass_guard(self):
        small_code = (
            "package main\n\n"
            "import \"fmt\"\n\n"
            "func Short() {\n"
            "    fmt.Println(\"short\")\n"
            "}\n"
        )
        file_path = "short.go"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(small_code)

        code = self.extractor.extract_function_code(file_path, "Short")
        self.assertEqual(code, small_code)

    def test_header_boilerplate_deduplication(self):
        dedup_code = (
            "#include <iostream>\n"
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include <vector>\n\n"
            "int main() { return 0; }\n"
        )
        file_path = "dedup.cpp"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(dedup_code)

        header = self.extractor.extract_import_header(file_path)
        self.assertIsNotNone(header)
        lines = header.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("#include <iostream>", lines)
        self.assertIn("#include <vector>", lines)

    def test_type_reference_auto_resolver(self):
        # Create a file over 50 lines to trigger AST slicing
        lines = ["// padding line " + str(i) for i in range(55)]
        type_code = (
            "#include <iostream>\n"
            "struct UserDTO {\n"
            "    int id;\n"
            "    std::string name;\n"
            "};\n\n" +
            "\n".join(lines) + "\n\n" +
            "void process_user(UserDTO dto) {\n"
            "    std::cout << dto.name;\n"
            "}\n"
        )
        file_path = "types_auto.cpp"
        with open(os.path.join(self.temp_dir, file_path), "w", encoding="utf-8") as f:
            f.write(type_code)

        code = self.extractor.extract_function_code(file_path, "process_user")
        self.assertIsNotNone(code)
        self.assertIn("process_user(UserDTO dto)", code)
        self.assertIn("// [AST_TYPE_AUTO_RESOLVED: UserDTO]", code)
        self.assertIn("struct UserDTO", code)

    def test_fault_tolerant_indexing(self):
        from build_graph import build_graph
        valid_py = "def valid_fn(): pass\n"
        invalid_tsx = "export function Bad() { return <div <<< corrupted >>> };\n"
        
        py_path = os.path.join(self.temp_dir, "valid.py")
        tsx_path = os.path.join(self.temp_dir, "invalid.tsx")
        
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(valid_py)
        with open(tsx_path, "w", encoding="utf-8") as f:
            f.write(invalid_tsx)

        # Ensure build_graph completes without throwing an exception
        graph = build_graph(self.temp_dir)
        self.assertIsNotNone(graph)

    def test_symbol_reverse_lookup(self):
        from build_graph import build_graph
        ts_code = (
            "export function createRedirectErrorDigest(response: any) {\n"
            "    return 'digest';\n"
            "}\n"
        )
        file_path = os.path.join(self.temp_dir, "errors.ts")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ts_code)

        graph = build_graph(self.temp_dir)
        symbol_index = graph.get("symbol_index", {})
        self.assertIn("createRedirectErrorDigest", symbol_index)
        self.assertIn("errors.ts", symbol_index["createRedirectErrorDigest"][0])

    def test_monorepo_path_normalization(self):
        from main import resolve_target_node
        graph = {
            "functions": {
                "packages/react-router/lib/errors.ts": ["createRedirectErrorDigest"]
            },
            "symbol_index": {
                "createRedirectErrorDigest": ["packages/react-router/lib/errors.ts"]
            }
        }
        res = resolve_target_node(graph, "FUNCTION:lib/errors.ts:createRedirectErrorDigest")
        self.assertIsNotNone(res)
        self.assertEqual(res["file"], "packages/react-router/lib/errors.ts")
        self.assertEqual(res["function"], "createRedirectErrorDigest")

    def test_batch_symbol_querying(self):
        import api.mcp_server as mcp_server
        lines = ["// padding line " + str(i) for i in range(55)]
        c_code = (
            "int fn_one() { return 1; }\n\n" +
            "\n".join(lines) + "\n\n" +
            "int fn_two() { return 2; }\n"
        )
        file_path = os.path.join(self.temp_dir, "batch.c")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(c_code)

        mcp_server.mcp_build_graph(self.temp_dir, force_rebuild=True, watch=False)
        res = mcp_server.mcp_query_context(targets=["FUNCTION:fn_one", "FUNCTION:fn_two"])
        self.assertIsNotNone(res)
        self.assertEqual(res.get("target_count"), 2)
        snippets = res.get("code_snippets", [])
        self.assertTrue(len(snippets) >= 2)

if __name__ == "__main__":
    unittest.main()
