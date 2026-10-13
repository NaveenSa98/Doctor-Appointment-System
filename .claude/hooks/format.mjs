// Claude Code PostToolUse hook: tidy a file right after Claude edits it.
// Python under backend/ -> ruff (fix + format). JS/JSX under frontend/src -> eslint --fix.
// Never blocks: a missing tool or a lint finding is reported on stderr and the edit stands.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

let input;
try {
  input = JSON.parse(readFileSync(0, 'utf8'));
} catch {
  process.exit(0);
}

const root = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const file = input?.tool_input?.file_path;
if (!file) process.exit(0);

const rel = path.relative(root, path.resolve(root, file)).split(path.sep).join('/');
const run = (cmd, args, cwd) => spawnSync(cmd, args, { cwd, encoding: 'utf8', shell: process.platform === 'win32' });

let results = [];
if (rel.startsWith('backend/') && rel.endsWith('.py')) {
  const target = rel.slice('backend/'.length);
  results = [
    run('uv', ['run', 'ruff', 'check', '--fix', target], path.join(root, 'backend')),
    run('uv', ['run', 'ruff', 'format', target], path.join(root, 'backend')),
  ];
} else if (rel.startsWith('frontend/src/') && /\.(js|jsx)$/.test(rel)) {
  const target = rel.slice('frontend/'.length);
  results = [run('npx', ['--no-install', 'eslint', '--fix', target], path.join(root, 'frontend'))];
}

const failed = results.find((r) => r.status !== 0);
if (failed) {
  process.stderr.write(`${rel}: ${(failed.stdout || failed.stderr || 'check failed').trim()}\n`);
  process.exit(2); // exit 2 shows stderr to Claude so it can fix the finding
}
