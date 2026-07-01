#!/usr/bin/env node
// Validates every workflows/**/workflow.json without needing a running n8n.
// Checks JSON validity, required node/connection structure, unique names & ids,
// and that every connection points at a node that actually exists.
// Exits non-zero on any error so CI fails the push/PR.

import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = 'workflows';
let hadError = false;

async function findWorkflowFiles(dir) {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...(await findWorkflowFiles(p)));
    else if (e.name.endsWith('.json')) out.push(p);
  }
  return out;
}

function err(msg) {
  console.error(`  ✖ ${msg}`);
  hadError = true;
}
function warn(msg) {
  console.warn(`  ⚠ ${msg}`);
}

function validate(wf) {
  if (typeof wf !== 'object' || wf === null || Array.isArray(wf)) {
    err('root is not an object');
    return;
  }
  if (!Array.isArray(wf.nodes) || wf.nodes.length === 0) err('"nodes" must be a non-empty array');
  if (typeof wf.connections !== 'object' || wf.connections === null || Array.isArray(wf.connections)) {
    err('"connections" must be an object');
  }
  if (!Array.isArray(wf.nodes)) return;

  const names = new Set();
  const ids = new Set();
  let triggerCount = 0;

  for (const [i, n] of wf.nodes.entries()) {
    const label = n && n.name ? `node "${n.name}"` : `node #${i}`;
    if (typeof n !== 'object' || n === null) {
      err(`${label} is not an object`);
      continue;
    }
    if (typeof n.name !== 'string' || !n.name) err(`${label}: missing "name"`);
    if (typeof n.type !== 'string' || !n.type) err(`${label}: missing "type"`);
    if (typeof n.typeVersion !== 'number') err(`${label}: "typeVersion" must be a number`);
    if (typeof n.id !== 'string' || !n.id) err(`${label}: missing "id"`);
    if (!Array.isArray(n.position) || n.position.length !== 2) err(`${label}: "position" must be [x, y]`);
    if (typeof n.parameters !== 'object' || n.parameters === null) err(`${label}: "parameters" must be an object`);

    if (n.name) {
      if (names.has(n.name)) err(`duplicate node name "${n.name}"`);
      names.add(n.name);
    }
    if (n.id) {
      if (ids.has(n.id)) err(`duplicate node id "${n.id}"`);
      ids.add(n.id);
    }
    if (typeof n.type === 'string' && (/trigger/i.test(n.type) || n.type.endsWith('.webhook') || n.type.endsWith('.manualTrigger'))) {
      triggerCount++;
    }
    if (n.credentials && typeof n.credentials === 'object') {
      for (const c of Object.values(n.credentials)) {
        if (c && typeof c === 'object' && c.id) {
          warn(`${label}: ships a credential id ("${c.id}") — templates should omit credential IDs`);
        }
      }
    }
  }

  if (triggerCount === 0) warn('no trigger node detected (fine for sub-workflows)');

  if (wf.connections && typeof wf.connections === 'object' && !Array.isArray(wf.connections)) {
    for (const [src, connByType] of Object.entries(wf.connections)) {
      if (!names.has(src)) err(`connection source "${src}" is not a defined node`);
      if (!connByType || typeof connByType !== 'object') continue;
      for (const [type, outputs] of Object.entries(connByType)) {
        if (!Array.isArray(outputs)) {
          err(`connections["${src}"]["${type}"] must be an array`);
          continue;
        }
        for (const group of outputs) {
          if (!Array.isArray(group)) continue;
          for (const c of group) {
            if (!c || typeof c.node !== 'string') {
              err(`connection from "${src}" has a malformed target`);
              continue;
            }
            if (!names.has(c.node)) err(`connection target "${c.node}" (from "${src}") is not a defined node`);
          }
        }
      }
    }
  }
}

const files = await findWorkflowFiles(ROOT);
if (files.length === 0) {
  console.error('No JSON files found under workflows/');
  process.exit(1);
}

console.log(`Scanning ${files.length} JSON file(s) under ${ROOT}/...\n`);
for (const file of files) {
  console.log(file);
  let raw;
  try {
    raw = await readFile(file, 'utf8');
  } catch (e) {
    err(`cannot read: ${e.message}`);
    console.log('');
    continue;
  }
  let wf;
  try {
    wf = JSON.parse(raw);
  } catch (e) {
    err(`invalid JSON: ${e.message}`);
    console.log('');
    continue;
  }
  // Only structurally validate files that are actually n8n workflow exports.
  // Other JSON under workflows/ (sample data, config maps) is parsed but skipped.
  if (!wf || typeof wf !== 'object' || !Array.isArray(wf.nodes)) {
    console.log('  – skipped (not an n8n workflow export)');
    console.log('');
    continue;
  }
  validate(wf);
  console.log('');
}

if (hadError) {
  console.error('Validation failed.');
  process.exit(1);
}
console.log('All workflows valid.');
