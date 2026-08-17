// VS Code client for the gear demo language. Spawns the generic fltk language server over
// stdio, straight from the local repo checkout. Provisional demo wiring, not for publication.

const path = require("path");
const { workspace } = require("vscode");
const { LanguageClient } = require("vscode-languageclient/node");

let client;

// <repo>/examples/gear/vscode/extension.js -> <repo>
function repoRoot() {
  return path.resolve(__dirname, "..", "..", "..");
}

// The in-repo default launch argv. The launcher builds //:fltk_lsp and execs the built
// server, so the running server holds no Bazel workspace lock. See examples/gear/README.md.
function defaultCommand() {
  const root = repoRoot();
  const gear = path.join(root, "examples", "gear");
  return [
    path.join(gear, "vscode", "run-gear-lsp"),
    "--grammar",
    path.join(gear, "gear.fltkg"),
    "--lsp",
    path.join(gear, "gear.fltklsp"),
    "--fmt",
    path.join(gear, "gear.fltkfmt"),
    "--resolver",
    path.join(gear, "gear_resolver.py") + ":create_resolver",
  ];
}

function serverCommand() {
  const override = workspace.getConfiguration("gear").get("server.command");
  if (Array.isArray(override) && override.length > 0) {
    return override;
  }
  return defaultCommand();
}

function activate(_context) {
  const argv = serverCommand();
  // No `transport` field: fltk-lsp is pygls-based and speaks stdio by default.
  // Setting transport: TransportKind.stdio would make vscode-languageclient append
  // a `--stdio` flag to the server argv (the convention for vscode-languageserver-node
  // servers), which pygls does not accept and rejects with exit code 2. Omitting
  // transport still uses stdio streams but appends no flag.
  const serverOptions = {
    command: argv[0],
    args: argv.slice(1),
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "gear" }],
  };

  client = new LanguageClient("gear", "gear language server", serverOptions, clientOptions);
  return client.start();
}

function deactivate() {
  if (!client) {
    return undefined;
  }
  return client.stop();
}

module.exports = { activate, deactivate };
