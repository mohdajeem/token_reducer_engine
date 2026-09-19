// Oracle for the JS precision audit: for each (file, byteOffset) call site, ask the TypeScript
// compiler (checkJs mode, so plain JS is inferred) where the callee is declared.
//   node ts_resolve_oracle.js <repoRoot> <requests.json>
// requests.json: [{"file": "src/x.js", "offset": 1234, "name": "tick"}]
// prints JSON: [{"file","offset","decls":[{"file","line"}]}]
const ts = require(process.env.TS_MODULE || "typescript");
const fs = require("fs");
const path = require("path");

const root = path.resolve(process.argv[2]);
const requests = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const files = [...new Set(requests.map(r => path.join(root, r.file)))];

// include the whole source tree so imports resolve
function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", ".git", "dist", "build", "coverage", ".semantic_cache"].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (/\.(js|jsx|ts|tsx|mjs|cjs)$/.test(e.name) && !/\.min\./.test(e.name)) out.push(p);
  }
  return out;
}
const rootFiles = walk(root, []);
const program = ts.createProgram(rootFiles, {
  allowJs: true, checkJs: true, noEmit: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
  moduleResolution: ts.ModuleResolutionKind.Bundler, allowSyntheticDefaultImports: true, esModuleInterop: true,
  jsx: ts.JsxEmit.Preserve, skipLibCheck: true, noResolve: false, maxNodeModuleJsDepth: 0,
});
const checker = program.getTypeChecker();

function findCallee(sf, offset) {
  // the call expression whose start is the byte offset; convert byte offset -> char offset
  const text = sf.getFullText();
  const buf = Buffer.from(text, "utf8");
  const charOffset = buf.slice(0, offset).toString("utf8").length;
  let best = null;
  function visit(n) {
    if ((ts.isCallExpression(n) || ts.isNewExpression(n)) && n.getStart(sf) === charOffset) { best = n; return; }
    if (n.getStart(sf) <= charOffset && charOffset < n.getEnd()) ts.forEachChild(n, visit);
  }
  visit(sf);
  if (!best) return null;
  let e = best.expression;
  if (ts.isPropertyAccessExpression(e)) return e.name;
  return e;
}

const out = [];
for (const r of requests) {
  const sf = program.getSourceFile(path.join(root, r.file));
  const res = { file: r.file, offset: r.offset, decls: [] };
  if (sf) {
    try {
      const node = findCallee(sf, r.offset);
      if (node) {
        let sym = checker.getSymbolAtLocation(node);
        if (sym && (sym.flags & ts.SymbolFlags.Alias)) sym = checker.getAliasedSymbol(sym);
        for (const d of (sym && sym.declarations) || []) {
          const dsf = d.getSourceFile();
          res.decls.push({ file: path.relative(root, dsf.fileName).replace(/\\/g, "/"), line: dsf.getLineAndCharacterOfPosition(d.getStart()).line + 1 });
        }
      }
    } catch (e) { res.error = String(e.message || e); }
  }
  out.push(res);
}
process.stdout.write(JSON.stringify(out));
