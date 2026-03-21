#!/usr/bin/env node

import { spawn, execFileSync } from "node:child_process";

function hasCommand(cmd) {
  try {
    execFileSync(cmd, ["--version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function run(cmd, args) {
  const child = spawn(cmd, args, {
    stdio: "inherit",
    env: process.env,
  });

  // Forward signals to child process
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.on(signal, () => child.kill(signal));
  }

  child.on("close", (code) => {
    process.exit(code ?? 1);
  });
}

const args = process.argv.slice(2);

if (hasCommand("uvx")) {
  run("uvx", ["bitcoin-mcp", ...args]);
} else if (hasCommand("pipx")) {
  run("pipx", ["run", "bitcoin-mcp", ...args]);
} else {
  console.error(
    `Error: bitcoin-mcp requires 'uvx' (from uv) or 'pipx' to run.

Install uv (recommended):
  curl -LsSf https://astral.sh/uv/install.sh | sh

Or install pipx:
  pip install pipx

Then retry:
  npx @bortlesboat/bitcoin-mcp`
  );
  process.exit(1);
}
