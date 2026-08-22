import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeCoreMap, readCoreMapSources } from "./core-map-normalizer.mjs";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const normalizedPath = join(repositoryRoot, "design", "shared", "pen", "inputs", "recipe-detail-core-map.json");
const penPath = join(repositoryRoot, "design", "shared", "pen", "recipe-detail-core-map.pen");
const normalizedRelativePath = relative(repositoryRoot, normalizedPath).replaceAll("\\", "/");
const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

const argument = (name) => {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
};

const stableJson = (value) => JSON.stringify(value);
const sha256 = (value) => createHash("sha256").update(stableJson(value)).digest("hex");
const semanticProjection = ({ generatedFrom: _generatedFrom, ...projection }) => projection;

const collectDiffPaths = (before, after, path = "") => {
  if (stableJson(before) === stableJson(after)) return [];

  if (
    before &&
    after &&
    typeof before === "object" &&
    typeof after === "object" &&
    !Array.isArray(before) &&
    !Array.isArray(after)
  ) {
    return [...new Set([...Object.keys(before), ...Object.keys(after)])]
      .flatMap((key) => collectDiffPaths(before[key], after[key], path ? `${path}.${key}` : key));
  }

  return [path];
};

const readGitJson = (ref, path) => {
  const safeDirectory = repositoryRoot.replaceAll("\\", "/");
  const text = execFileSync(
    "git",
    ["-c", `safe.directory=${safeDirectory}`, "show", `${ref}:${path}`],
    { cwd: repositoryRoot, encoding: "utf8" }
  );
  return JSON.parse(text);
};

const firstRun = normalizeCoreMap(await readCoreMapSources(repositoryRoot));
const secondRun = normalizeCoreMap(await readCoreMapSources(repositoryRoot));
const committed = JSON.parse(await readFile(normalizedPath, "utf8"));
const pen = JSON.parse(await readFile(penPath, "utf8"));

assert(stableJson(firstRun) === stableJson(secondRun), "identical-input normalization changed between runs");
assert(stableJson(firstRun) === stableJson(committed), "committed normalized input is not current generated output");

const nodeIds = firstRun.journeys.flatMap((journey) => journey.nodes.map((node) => node.id));
const penStableIds = [];
const penImageCount = { value: 0 };
const walkPen = (value) => {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    value.forEach(walkPen);
    return;
  }
  if (value.type === "design-graph-node") penStableIds.push(value.stableId);
  if (value.type === "image") penImageCount.value += 1;
  Object.values(value).forEach(walkPen);
};
walkPen(pen);

assert(new Set(nodeIds).size === nodeIds.length, "normalized input contains duplicate node IDs");
assert(new Set(penStableIds).size === penStableIds.length, "Pen projection contains duplicate stable IDs");
assert(stableJson([...nodeIds].sort()) === stableJson([...penStableIds].sort()), "Pen stable IDs do not match normalized Core nodes");

const beforeRef = argument("--before-ref");
let controlledChange = "not requested";
if (beforeRef) {
  const before = readGitJson(beforeRef, normalizedRelativePath);
  const diffPaths = collectDiffPaths(before, committed);
  const allowedDiffPaths = new Set(["generatedFrom.asOf", "generatedFrom.sourceRevision"]);
  const unexpectedDiffPaths = diffPaths.filter((path) => !allowedDiffPaths.has(path));
  assert(sha256(semanticProjection(before)) === sha256(semanticProjection(committed)), "controlled source change altered Core semantics");
  assert(unexpectedDiffPaths.length === 0, `controlled source change has unexpected fields: ${unexpectedDiffPaths.join(", ")}`);
  controlledChange = `${beforeRef} -> working tree; raw fields changed: ${diffPaths.join(", ") || "none"}`;
}

if (failures.length) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.log(`Verified Core regeneration: identical normalized SHA ${sha256(firstRun)}; semantic SHA ${sha256(semanticProjection(firstRun))}.`);
console.log(`Controlled source change: ${controlledChange}; semantic changes: none.`);
console.log(`Pen semantic projection: ${penStableIds.length} stable graph nodes, ${penImageCount.value} image fills; normalized graph remains independently readable.`);
