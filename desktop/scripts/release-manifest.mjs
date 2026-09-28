#!/usr/bin/env node
// Release helpers shared by CI (.github/workflows/desktop-build.yml) and the
// macOS cross-compile script. No dependencies.
//
//   node scripts/release-manifest.mjs check-version [tag]
//       Fails unless package.json, tauri.conf.json and Cargo.toml agree, and
//       (when given) the tag is desktop-v<version>. A mismatch would ship an
//       installer whose updater thinks it is a different version.
//
//   node scripts/release-manifest.mjs latest-json <version> <notes> <sig-file> <url> <out>
//       Writes the Tauri updater manifest (latest.json) for one Windows asset.

import { readFileSync, writeFileSync } from "node:fs";

const desktop = new URL("../", import.meta.url).pathname;
const [cmd, ...args] = process.argv.slice(2);

function versions() {
  const pkg = JSON.parse(readFileSync(`${desktop}package.json`, "utf8")).version;
  const conf = JSON.parse(readFileSync(`${desktop}src-tauri/tauri.conf.json`, "utf8")).version;
  const cargo = /^version\s*=\s*"([^"]+)"/m.exec(readFileSync(`${desktop}src-tauri/Cargo.toml`, "utf8"))?.[1];
  return { "package.json": pkg, "tauri.conf.json": conf, "Cargo.toml": cargo };
}

if (cmd === "check-version") {
  const v = versions();
  const distinct = new Set(Object.values(v));
  if (distinct.size !== 1) {
    console.error(`Version mismatch: ${JSON.stringify(v)}`);
    process.exit(1);
  }
  const [version] = distinct;
  const tag = args[0];
  if (tag && tag !== `desktop-v${version}`) {
    console.error(`Tag ${tag} doesn't match version ${version} (expected desktop-v${version}).`);
    process.exit(1);
  }
  console.log(version);
} else if (cmd === "latest-json") {
  const [version, notes, sigPath, url, outPath] = args;
  const manifest = {
    version,
    notes,
    pub_date: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    platforms: { "windows-x86_64": { signature: readFileSync(sigPath, "utf8").trim(), url } },
  };
  writeFileSync(outPath, JSON.stringify(manifest, null, 2) + "\n");
  console.log(`wrote ${outPath}`);
} else {
  console.error("usage: release-manifest.mjs check-version [tag] | latest-json <version> <notes> <sig> <url> <out>");
  process.exit(2);
}
