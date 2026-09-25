# Blast Radius — a semantic code graph for AI coding agents

An MCP server that gives an AI coding agent a graph of the codebase instead of a search box.
It answers the three questions file search cannot:

- **what does this change reach?** — callers, callees, and the edges in between
- **which tests cover it?** — the tests that actually execute the code being changed
- **what is the smallest context that still contains the fix?** — function-level slices, not whole files

Python · JavaScript · TypeScript · Java.

Landing page: <https://blast-radius-topaz.vercel.app/>

---

## Why a graph

Text search finds the word `validate`. It does not know that `URLValidator.regex` is read by a
base class's `__call__`, that the base class is driven through a dependency-injected field, and
that three tests reach it. A graph does — and that is the difference between handing a model the
right 400 lines and handing it four whole files.

Every edge carries a **confidence** label — `observed` (seen at runtime) > `resolved` >
`dispatch` / `convention` > `unobserved` — so a caller can ask for only what it trusts:

```python
mcp_impact_analysis(target="FUNCTION:src/api.py:Session.request", min_confidence="resolved")
```

## What it measures on real code

Share of call sites resolved to project code, or correctly labelled as library/builtin —
one real repository per language:

| Language | Repository | Before | After |
|---|---|---:|---:|
| Java | spring-petclinic | 14% | **94%** |
| TypeScript | nestjs/nest (core) | 59% | **90%** |
| Python | SWE-bench repos | — | ~90% |
| JavaScript | marked, p5.js, Chart.js | ~40% | ~85% |

Against [Agentless](https://github.com/OpenAutoCoder/Agentless) (UIUC), scored on the same 30
SWE-bench Verified tasks using their published run artifacts:

| | Agentless | Blast Radius |
|---|---:|---:|
| Fix's file in the top 5 | **97%** | 87% |
| Fix's function identified | **80%** | 63% |
| Regression suite kept to re-run (median) | 88% | **16%** |
| Tests kept that the fix is meant to change (lower is better) | 463 | **9** |
| Model calls to produce that answer | 3 / task | **0** |

Read honestly: a three-prompt LLM pipeline still localises better, because it understands the
issue text. The graph wins downstream — a regression suite a fifth the size, keeping 50x fewer of
the tests the fix is meant to change (9 against 463), at zero inference cost. Combining the two
file lists found the right file on all 30 tasks, which neither managed alone.

The graph's own failure is the opposite one: on 4 of the 30 tasks it selects no tests at all.
Safe, and useless.

Prompt size, measured the other way round — the same agent, same tasks, once reading whole
files and once reading the engine's slices, with the target symbol given in both arms:

| | baseline | engine |
|---|---:|---:|
| Input tokens, 610 tasks | 39.5M | **1.1M** |
| Tasks passed | parity | parity |

That 97% holds **when the target symbol is known** — an IDE assistant, a code review, a
refactor. An agent that must first find the bug from an issue description pays for the search,
and the saving does not survive it; see Known limits.

## A worked example

Django issue #10097: *"Make URLValidator reject invalid characters in the username and password."*
The real fix is one line, and it is not in a function at all — it edits a **class attribute**:

```python
class URLValidator(RegexValidator):
    regex = _lazy_re_compile(
-       r'(?:\S+(?::\S*)?@)?'            # \S+ allows "/" and "@" in the username
+       r'(?:[^\s:@/]+(?::[^\s:@/]*)?@)?'
```

Ask the engine what that line reaches:

```python
mcp_tests_for(target="FUNCTION:django/core/validators.py:URLValidator.regex", hops=4)
```

```json
{
  "level": "function",
  "tests": [
    {"file": "tests/validators/tests.py", "function": "test_unicode_validator"},
    {"file": "tests/validators/tests.py", "function": "test_ascii_validator"},
    {"file": "tests/auth_tests/test_validators.py", "function": "test_all_errors_get_reported"}
    // 21 in total
  ]
}
```

It gets there by following edges no text search produces: `URLValidator.regex` is read as
`self.regex` inside `RegexValidator.__call__` — a **method on the base class** — and
`URLValidator` **overrides** the attribute it reads. Both hops are edges in the graph
(`confidence: "uses"`, `via: "attribute"`).

Before class attributes were nodes, that same query returned an error and regression selection for
this task returned *no tests at all*. The fixture that pins this behaviour is `py-class-attribute`
in `src/tests/test_patterns.py`.

**And where it still loses.** Django generates most of its validator tests at import time —
a loop reads URLs out of `tests/validators/invalid_urls.txt` and attaches one test function per
line with `setattr`. Those 438 test functions exist in no source file, so no static parser can
name them. That is what the optional trace layer is for.

## Tools exposed over MCP

| Tool | Answers |
|---|---|
| `mcp_build_graph` | parse a repository (incremental on later calls) |
| `mcp_find_symbols` | rank files and symbols against free text |
| `mcp_skeleton` | one file's symbols, signatures and spans — bodies on demand |
| `mcp_query_context` | the pruned code for a symbol and its chain |
| `mcp_impact_analysis` | blast radius, filterable by confidence |
| `mcp_tests_for` | the tests that reach a symbol (function level, file-level fallback) |
| `mcp_file_dependents` | who imports this file |
| `mcp_neighbors`, `mcp_expand_signature`, `mcp_show_routes`, `mcp_show_graph_metrics` | navigation and diagnostics |

## Running it

```bash
pip install -r requirements.txt
python src/api/mcp_server.py          # speaks MCP over stdio
```

Point any MCP-capable client at it. For the OpenHands agent SDK:

```json
{
  "mcp": {
    "semantic_engine": {
      "command": "python",
      "args": ["src/api/mcp_server.py"],
      "env": { "PYTHONPATH": "src", "SEMANTIC_INDEX_TESTS": "1" }
    }
  }
}
```

## Tests

Each defect this engine ever had is pinned by a fixture — a small repository reproducing the
exact code shape that broke it, taken from the real project where it was found.

```bash
python src/tests/test_patterns.py            # 52 fixtures: stored methods, dunder calls, DI fields,
                                             # Spring routes, generated test titles, class attributes
python src/tests/test_py_graph_quality.py
python src/tests/test_js_graph_quality.py
python src/tests/test_java_graph_quality.py
python src/tests/test_ts_graph_quality.py
python src/tests/test_incremental_equivalence.py
python src/tests/test_dynamic_trace.py
python src/tests/run_all_tests.py
```

## Known limits

- **Runtime-generated code is invisible to static parsing.** Django builds hundreds of test
  functions with `setattr` in a loop, from URLs read out of a `.txt` file; nothing in the source
  names them. The optional trace layer (`src/dynamic_trace/`) records one real test run and merges
  observed edges into the graph, which is the only way to see them.
- Localisation is keyword + graph evidence, with no semantic reading of the issue text — which is
  why an LLM pipeline still beats it at that one step.
- Go, Rust, C and C++ have query files but have not been through the fixture loop; expect early
  Java-level accuracy there.
- Per-language figures come from one repository each, and the SWE-bench figures from 30 tasks.
  Directions are solid; treat the exact percentages as approximate.
- **The 97% prompt reduction does not transfer to unguided bug fixing.** Measured on 6 SWE-bench
  Verified tasks across 6 repositories, with the agent finding the target itself, the median
  change in tokens was zero — the extra lookups needed to locate the symbol cost about what the
  smaller context saves. What did improve was the worst case: the widest run used 608k tokens
  against the baseline's 1.72M.
- Regression selection returns nothing on roughly 1 task in 8 (4 of 30), usually where the
  changed symbol is a class attribute or the tests are generated at import time.

## Layout

```
src/semantic_core/        parsing, symbol resolution, graph construction
src/impact_engine/        traversal and confidence policy
src/context_engine/       code extraction and pruning
src/incremental_runtime/  incremental rebuilds, snapshots, change detection
src/dynamic_trace/        optional runtime tracer and merge
src/queries/              tree-sitter queries per language
src/api/mcp_server.py     the MCP server
src/tests/                fixtures and quality suites
docs/                     architecture and per-module guides
```

---

Mohd Ajeem · [mohdajeem2003@gmail.com](mailto:mohdajeem2003@gmail.com)
