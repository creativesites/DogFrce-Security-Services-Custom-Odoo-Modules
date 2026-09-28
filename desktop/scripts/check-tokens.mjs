#!/usr/bin/env node
// Design-token guard (DG-ADR-017, RECONCILIATION.md §E).
//
// Fails when:
//   1. a stylesheet other than the token sources (ds.css, dgs.css) contains a
//      raw hex colour, or
//   2. any stylesheet or TSX file reads a `var(--x)` custom property that no
//      stylesheet defines. In 2026-09 twelve such undefined tokens left newer
//      screens partly unstyled with nothing to catch it.
//
// Runs as part of `npm run lint`. No dependencies.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = new URL("../src/", import.meta.url).pathname;
const TOKEN_SOURCES = new Set(["styles/ds.css", "styles/dgs.css"]);

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

const files = walk(root).filter((f) => /\.(css|tsx?)$/.test(f) && !/\.test\.tsx?$/.test(f));
const css = files.filter((f) => f.endsWith(".css"));

const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "");

const defined = new Set();
for (const f of css) {
  for (const m of stripComments(readFileSync(f, "utf8")).matchAll(/(--[\w-]+)\s*:/g)) defined.add(m[1]);
}

const problems = [];
for (const f of files) {
  const rel = relative(root, f);
  const text = f.endsWith(".css") ? stripComments(readFileSync(f, "utf8")) : readFileSync(f, "utf8");

  if (f.endsWith(".css") && !TOKEN_SOURCES.has(rel)) {
    for (const m of text.matchAll(/#[0-9a-fA-F]{3,8}\b/g)) {
      problems.push(`${rel}: raw colour ${m[0]} (use a --ds-*/--dgs-* token)`);
    }
  }
  for (const m of text.matchAll(/var\(\s*(--[\w-]+)\s*(,[^)]*)?\)/g)) {
    // A var() with a fallback is allowed to reference an optional token.
    if (!defined.has(m[1]) && !m[2]) problems.push(`${rel}: ${m[1]} is used but never defined`);
  }
}

if (problems.length) {
  console.error(`Design-token check failed (${problems.length}):\n  ${[...new Set(problems)].join("\n  ")}`);
  process.exit(1);
}
console.log(`Design tokens OK (${files.length} files, ${defined.size} tokens defined).`);
