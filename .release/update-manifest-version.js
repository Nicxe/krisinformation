const fs = require("fs");

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    const value = argv[i + 1];
    out[key] = value;
    i += 1;
  }
  return out;
}

function detectNewline(text) {
  return text.includes("\r\n") ? "\r\n" : "\n";
}

function upsertVersionPreservingFormat(text, version) {
  const existing = /("version"\s*:\s*")([^"]*)(")/m;
  if (existing.test(text)) {
    return text.replace(existing, `$1${version}$3`);
  }

  const newline = detectNewline(text);
  const isMultiline = text.includes("\n");

  if (!isMultiline) {
    const lastBrace = text.lastIndexOf("}");
    if (lastBrace === -1) return text;

    const beforeBrace = text.slice(0, lastBrace);
    const afterBrace = text.slice(lastBrace);

    const openBrace = beforeBrace.indexOf("{");
    const inside = openBrace === -1 ? "" : beforeBrace.slice(openBrace + 1).trim();
    const needsComma = inside.length > 0 && !inside.endsWith(",");

    const insertion = `${needsComma ? "," : ""} "version": "${version}"`;
    return `${beforeBrace}${insertion}${afterBrace}`;
  }

  const lines = text.split(/\r?\n/);

  let closeIdx = lines.length - 1;
  while (closeIdx > 0 && lines[closeIdx].trim() === "") closeIdx -= 1;
  if (lines[closeIdx].trim() !== "}") {
    return text;
  }

  const indentMatch = text.match(/^[ \t]+(?="[^"]+"\s*:)/m);
  const indent = indentMatch ? indentMatch[0] : "  ";

  let propIdx = closeIdx - 1;
  while (propIdx >= 0 && !/:\s*/.test(lines[propIdx])) propIdx -= 1;

  if (propIdx >= 0 && !lines[propIdx].trim().endsWith(",")) {
    lines[propIdx] = `${lines[propIdx].replace(/\s*$/, "")},`;
  }

  lines.splice(closeIdx, 0, `${indent}"version": "${version}"`);
  return lines.join(newline);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const file = args.file;
  const versionRaw = args.version;

  if (!file || !versionRaw) {
    // eslint-disable-next-line no-console
    console.error(
      "Usage: node .release/update-manifest-version.js --file <path> --version <version>"
    );
    process.exit(2);
  }

  const version = String(versionRaw);

  if (!fs.existsSync(file)) {
    throw new Error(`File not found: ${file}`);
  }

  const before = fs.readFileSync(file, "utf8");
  const after = upsertVersionPreservingFormat(before, version);

  if (after === before) {
    let parsed;
    try {
      parsed = JSON.parse(before);
    } catch (e) {
      throw new Error(
        `Could not update or insert "version" field in ${file} (unexpected format)`
      );
    }
    if (String(parsed?.version ?? "") === String(version)) {
      return;
    }
    throw new Error(
      `Could not update or insert "version" field in ${file} (unexpected format)`
    );
  }

  JSON.parse(after);
  fs.writeFileSync(file, after);
}

main();

