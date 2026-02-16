#!/usr/bin/env node
// Windows-compatible entry point for the Auto-Explorer stop hook.
// Resolves Git Bash explicitly to avoid WSL bash being picked up on Windows.
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const pluginRoot = (process.argv[2] || "").replace(/\\/g, "/");
const scriptPath = pluginRoot + "/hooks/stop-hook.sh";

function findGitBash() {
  const candidates = [
    path.join(
      process.env.PROGRAMFILES || "C:\\Program Files",
      "Git",
      "usr",
      "bin",
      "bash.exe"
    ),
    path.join(
      process.env.PROGRAMFILES || "C:\\Program Files",
      "Git",
      "bin",
      "bash.exe"
    ),
    path.join(
      process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)",
      "Git",
      "usr",
      "bin",
      "bash.exe"
    ),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return "bash"; // fallback
}

const isWindows = process.platform === "win32";
const bashPath = isWindows ? findGitBash() : "bash";

// On Windows, ensure MSYS/Git tools (cat, grep, sed, etc.) are in PATH,
// and force UTF-8 encoding to prevent CJK mojibake (default codepage is often CP950/Big5).
const env = { ...process.env };
if (isWindows) {
  const gitDir = process.env.PROGRAMFILES
    ? path.join(process.env.PROGRAMFILES, "Git")
    : "C:\\Program Files\\Git";
  const msysPaths = [
    path.join(gitDir, "usr", "bin"),
    path.join(gitDir, "mingw64", "bin"),
  ];
  const currentPath = env.PATH || env.Path || "";
  const missing = msysPaths.filter(
    (p) => !currentPath.toLowerCase().includes(p.toLowerCase())
  );
  if (missing.length) {
    const pathKey = "PATH" in env ? "PATH" : "Path";
    env[pathKey] = missing.join(";") + ";" + currentPath;
  }
  // Force UTF-8 for bash and Python subprocesses
  env.LANG = "C.UTF-8";
  env.LC_ALL = "C.UTF-8";
  env.PYTHONIOENCODING = "utf-8";
}

try {
  execFileSync(bashPath, ["--login", scriptPath], {
    stdio: "inherit",
    env,
  });
} catch (e) {
  process.exit(e.status || 1);
}
