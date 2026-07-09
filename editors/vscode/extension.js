// VS Code client for fltk's own grammar DSLs (.fltkg / .fltkfmt / .fltklsp).
// One LanguageClient per language, each spawning fltk-grammar-lsp over stdio via uv,
// started lazily when the first document of that language appears. In-repo wiring,
// not for publication.

const path = require("path");
const { workspace, window } = require("vscode");
const { LanguageClient } = require("vscode-languageclient/node");

const LANGUAGES = ["fltkg", "fltkfmt", "fltklsp"];

// languageId -> LanguageClient, one per fltk language actually opened this session.
const clients = new Map();

// <repo>/editors/vscode/extension.js -> <repo>
function repoRoot() {
  return path.resolve(__dirname, "..", "..");
}

// The in-repo default launch argv prefix; the language id is appended per client.
// `--extra lsp` is load-bearing: pygls lives only in the `lsp` optional extra, and plain
// `uv run` syncs default groups only, so without it a clean checkout gets a pygls-less
// environment and the server exits before any protocol I/O. See editors/vscode/README.md.
function commandPrefix() {
  const override = workspace.getConfiguration("fltk.grammars").get("server.command");
  if (Array.isArray(override) && override.length > 0) {
    return override;
  }
  return ["uv", "--project", repoRoot(), "run", "--extra", "lsp", "fltk-grammar-lsp"];
}

function startClient(languageId) {
  if (clients.has(languageId)) {
    return;
  }
  const argv = [...commandPrefix(), languageId];
  // No `transport` field: fltk-grammar-lsp is pygls-based and speaks stdio by default.
  // Setting transport: TransportKind.stdio would make vscode-languageclient append a
  // `--stdio` flag to the server argv, which pygls rejects with exit code 2. Omitting
  // transport still uses stdio streams but appends no flag.
  const serverOptions = {
    command: argv[0],
    args: argv.slice(1),
  };
  const clientOptions = {
    documentSelector: [{ scheme: "file", language: languageId }],
  };
  const client = new LanguageClient(
    "fltkGrammars." + languageId,
    "fltk " + languageId + " language server",
    serverOptions,
    clientOptions,
  );
  clients.set(languageId, client);
  // If the server fails to launch (uv missing, bad server.command, pygls-less env, transient
  // contention), surface it and drop the dead client so a later document-open can retry rather
  // than caching a permanently-broken client for the whole session.
  client.start().catch((err) => {
    clients.delete(languageId);
    window.showErrorMessage(
      "fltk " + languageId + " language server failed to start: " + (err && err.message ? err.message : err),
    );
  });
}

function maybeStart(document) {
  if (document && LANGUAGES.includes(document.languageId)) {
    startClient(document.languageId);
  }
}

function activate(context) {
  workspace.textDocuments.forEach(maybeStart);
  context.subscriptions.push(workspace.onDidOpenTextDocument(maybeStart));
}

function deactivate() {
  const stops = [];
  for (const client of clients.values()) {
    stops.push(client.stop());
  }
  clients.clear();
  return Promise.all(stops);
}

module.exports = { activate, deactivate };
