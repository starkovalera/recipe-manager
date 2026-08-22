import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const graphRoot = join(repositoryRoot, "design", "shared", "design-graph");
const inputPath = join(repositoryRoot, "design", "shared", "pen", "inputs", "recipe-detail-core-map.json");
const reviewPath = join(repositoryRoot, "design", "shared", "pen", "core-map-review.md");
const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));
const exists = async (path) => {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
};

const graph = await readJson(join(graphRoot, "graph.json"));
const schema = await readJson(join(graphRoot, "schema.json"));
const domain = await readJson(join(graphRoot, graph.domains[0].source));
const github = await readJson(join(graphRoot, graph.snapshots[0].source));
const normalized = await readJson(inputPath);
const review = await readFile(reviewPath, "utf8");
const failures = [];
const withoutPen = process.argv.includes("--without-pen");
const assert = (condition, message) => { if (!condition) failures.push(message); };
const repositoryPath = (path) => !path.includes("://");

assert(schema.properties.schemaVersion.const === graph.schemaVersion, "schemaVersion must match schema.json");
assert(JSON.stringify(graph.precedence) === JSON.stringify(["current_decision", "github_snapshot", "canonical_roadmap", "evidence"]), "source precedence changed unexpectedly");
assert(graph.domains[0].source === "domains/recipe-detail-core-map.json", "active graph domain must be the Core map");
assert(domain.id === graph.domains[0].id, "domain id must match graph reference");
assert(domain.iteration === "core", "active domain must be the Core iteration");
assert(domain.platform === "desktop_web", "Core map must remain desktop_web");
assert(domain.nodes.length >= 20 && domain.nodes.length <= 30, "Core map must contain 20–30 nodes");
assert(domain.journeys.length === 3, "Core map must contain exactly three journeys");

const designStatuses = new Set(["not_started", "in_progress", "blocked", "awaiting_approval", "approved", "verification_needed"]);
const deliveryStatuses = new Set(["not_planned", "blocked", "ready", "in_progress", "delivered", "verification_needed"]);
const scopes = new Set(["approved", "placeholder"]);
const journeyIds = new Set(domain.journeys.map((journey) => journey.id));
const nodeIds = new Set();
const warningIds = new Set(domain.warnings.map((warning) => warning.id));
const githubIssues = new Set(github.issues.map((issue) => issue.number));
const githubPullRequests = new Set(github.pullRequests.map((pullRequest) => pullRequest.number));
const screenshotNodes = new Set();

for (const journey of domain.journeys) {
  assert(/^journey\.[a-z0-9-]+$/.test(journey.id), `invalid journey id: ${journey.id}`);
  assert(domain.nodes.some((node) => node.journeyId === journey.id), `journey has no nodes: ${journey.id}`);
}

for (const node of domain.nodes) {
  assert(/^recipe-detail\.[a-z0-9-]+\.[a-z0-9-]+$/.test(node.id), `invalid node id: ${node.id}`);
  assert(!nodeIds.has(node.id), `duplicate node id: ${node.id}`);
  nodeIds.add(node.id);
  assert(journeyIds.has(node.journeyId), `unknown journey on ${node.id}`);
  assert(scopes.has(node.scope), `invalid scope on ${node.id}`);
  assert(designStatuses.has(node.designStatus), `invalid Design status on ${node.id}`);
  assert(deliveryStatuses.has(node.deliveryStatus), `invalid Delivery status on ${node.id}`);
  assert(node.sources.decisions.length > 0, `missing decision evidence on ${node.id}`);
  assert(Boolean(node.sources.prototype), `missing prototype evidence on ${node.id}`);
  assert(node.sources.issues.every((number) => githubIssues.has(number)), `missing issue snapshot on ${node.id}`);
  assert(node.sources.pullRequests.every((number) => githubPullRequests.has(number)), `missing PR snapshot on ${node.id}`);
  assert(node.scope === "placeholder" ? node.designStatus === "not_started" : node.designStatus === "approved", `scope/status mismatch on ${node.id}`);
  if (node.scope === "placeholder") {
    assert(node.deliveryStatus === "blocked", `placeholder must be delivery-blocked on ${node.id}`);
    assert(Boolean(node.scopeNote), `placeholder missing scopeNote on ${node.id}`);
  }
  if (node.sources.screenshot) screenshotNodes.add(node.id);
  for (const warningId of node.verificationNeeded ?? []) {
    assert(warningIds.has(warningId), `unknown warning ${warningId} on ${node.id}`);
  }
}

for (const transition of domain.transitions) {
  assert(nodeIds.has(transition.from) || transition.from === "entry.recipes", `unknown transition source: ${transition.id}`);
  assert(nodeIds.has(transition.to), `unknown transition target: ${transition.id}`);
  assert(["native", "docs-derived", "curated"].includes(transition.provenance), `invalid transition provenance: ${transition.id}`);
  assert(Boolean(transition.label), `missing transition label: ${transition.id}`);
}

for (const path of [
  ...domain.nodes.flatMap((node) => node.sources.decisions),
  ...domain.nodes.map((node) => node.sources.prototype),
  ...domain.nodes.map((node) => node.sources.screenshot).filter(Boolean)
]) {
  assert(repositoryPath(path), `evidence path must not be an external URL: ${path}`);
  try {
    await access(join(repositoryRoot, path));
  } catch {
    failures.push(`missing repository evidence: ${path}`);
  }
}

const corePenPath = join(repositoryRoot, "design", "shared", "pen", "recipe-detail-core-map.pen");
if (!withoutPen) {
  assert(
    await exists(corePenPath) || review.includes("Status: awaiting owner checkpoint"),
    "missing Core Pen file must retain an explicit awaiting-owner checkpoint"
  );
  assert(
    await exists(join(repositoryRoot, "design", "shared", "pen", "exports", "recipe-detail-core-map.png")),
    "missing derived Core Pen export: design/shared/pen/exports/recipe-detail-core-map.png"
  );
}

assert(domain.reviewSelection.length >= 8, "review selection must contain a coherent screenshot subset");
assert(domain.reviewSelection.every((id) => nodeIds.has(id)), "review selection contains an unknown node");
assert(domain.reviewSelection.every((id) => screenshotNodes.has(id)), "review selection must use nodes with screenshots");
assert(new Set(domain.placeholderNodes).size === domain.placeholderNodes.length, "duplicate placeholder node");
assert(domain.placeholderNodes.every((id) => nodeIds.has(id)), "placeholder list contains an unknown node");
assert(domain.placeholderNodes.every((id) => domain.nodes.find((node) => node.id === id)?.scope === "placeholder"), "placeholder list contains an approved node");

assert(normalized.map.iteration === "core", "normalized input lost Core iteration");
assert(normalized.journeys.length === 3, "normalized input lost a journey");
assert(normalized.journeys.flatMap((journey) => journey.nodes).length === domain.nodes.length, "normalized input lost a node");
assert(normalized.reviewSelection.length === domain.reviewSelection.length, "normalized input lost review selection");
assert(normalized.placeholderNodes.length === domain.placeholderNodes.length, "normalized input lost placeholder list");
assert(normalized.warnings.some((warning) => warning.id === "warning.roadmap-pr80-state"), "roadmap contradiction must remain visible");
assert(normalized.warnings.some((warning) => warning.id === "warning.import-review-contract"), "Import review contradiction must remain visible");

if (failures.length) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

const persistence = withoutPen
  ? "Pen artifacts not required (--without-pen)"
  : await exists(corePenPath)
    ? "repository Core Pen file present"
    : "repository Core Pen file pending owner Save As";
console.log(`Validated Core map: ${domain.nodes.length} nodes, ${domain.transitions.length} transitions, ${domain.warnings.length} warnings, ${domain.reviewSelection.length} review screenshots, all repository evidence links, and ${persistence}.`);
