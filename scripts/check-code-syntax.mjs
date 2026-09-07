#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const workflowDir = path.join(scriptDir, "..", "workflows");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

let checked = 0;
const failures = [];

for (const file of fs.readdirSync(workflowDir).filter((name) => name.endsWith(".json")).sort()) {
  const workflow = JSON.parse(fs.readFileSync(path.join(workflowDir, file), "utf8"));
  for (const node of workflow.nodes ?? []) {
    const code = node?.parameters?.jsCode ?? node?.parameters?.functionCode;
    if (typeof code !== "string" || code.trim() === "") continue;
    checked += 1;
    try {
      new AsyncFunction(code);
    } catch (error) {
      failures.push(`${file} :: ${node.name} :: ${error.message}`);
    }
  }
}

if (failures.length) {
  console.error(`FAILED: ${failures.length} Code node(s) contain invalid JavaScript`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`PASS: JavaScript syntax compiled for ${checked} Code node(s)`);

