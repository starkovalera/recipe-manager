import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const graphRoot = join(repositoryRoot, "design", "shared", "design-graph");
const inputPath = join(repositoryRoot, "design", "shared", "pen", "inputs", "recipe-detail-first-map.json");
const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));

const graph = await readJson(join(graphRoot, "graph.json"));
const schema = await readJson(join(graphRoot, "schema.json"));
const domain = await readJson(join(graphRoot, graph.domains[0].source));
const github = await readJson(join(graphRoot, graph.snapshots[0].source));
const normalized = await readJson(inputPath);
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

assert(schema.properties.schemaVersion.const === graph.schemaVersion, "schemaVersion must match schema.json");
assert(JSON.stringify(graph.precedence) === JSON.stringify(["current_decision", "github_snapshot", "canonical_roadmap", "evidence"]), "source precedence changed unexpectedly");
assert(domain.id === graph.domains[0].id, "domain id must match graph reference");
assert(domain.platform === "desktop_web", "First map must remain desktop_web");
assert(domain.nodes.length >= 8 && domain.nodes.length <= 12, "First map must contain 8–12 nodes");
assert(domain.journeys.length === 3, "First map must contain exactly three journeys");

const designStatuses = new Set(["not_started", "in_progress", "blocked", "awaiting_approval", "approved", "verification_needed"]);
const deliveryStatuses = new Set(["not_planned", "blocked", "ready", "in_progress", "delivered", "verification_needed"]);
const journeyIds = new Set(domain.journeys.map((journey) => journey.id));
const nodeIds = new Set();
const warningIds = new Set(domain.warnings.map((warning) => warning.id));
const githubIssues = new Set(github.issues.map((issue) => issue.number));
const githubPullRequests = new Set(github.pullRequests.map((pullRequest) => pullRequest.number));

for (const journey of domain.journeys) {
  assert(/^journey\.[a-z0-9-]+$/.test(journey.id), `invalid journey id: ${journey.id}`);
  assert(domain.nodes.some((node) => node.journeyId === journey.id), `journey has no nodes: ${journey.id}`);
}

for (const node of domain.nodes) {
  assert(/^recipe-detail\.[a-z0-9-]+\.[a-z0-9-]+$/.test(node.id), `invalid node id: ${node.id}`);
  assert(!nodeIds.has(node.id), `duplicate node id: ${node.id}`);
  nodeIds.add(node.id);
  assert(journeyIds.has(node.journeyId), `unknown journey on ${node.id}`);
  assert(designStatuses.has(node.designStatus), `invalid Design status on ${node.id}`);
  assert(deliveryStatuses.has(node.deliveryStatus), `invalid Delivery status on ${node.id}`);
  assert(node.sources.decisions.length > 0, `missing decision evidence on ${node.id}`);
  assert(Boolean(node.sources.prototype), `missing prototype evidence on ${node.id}`);
  assert(node.sources.issues.every((number) => githubIssues.has(number)), `missing issue snapshot on ${node.id}`);
  assert(node.sources.pullRequests.every((number) => githubPullRequests.has(number)), `missing PR snapshot on ${node.id}`);
  for (const warningId of node.verificationNeeded ?? []) {
    assert(warningIds.has(warningId), `unknown warning ${warningId} on ${node.id}`);
  }
}

for (const transition of domain.transitions) {
  assert(nodeIds.has(transition.from) || transition.from === "entry.recipes", `unknown transition source: ${transition.id}`);
  assert(nodeIds.has(transition.to), `unknown transition target: ${transition.id}`);
  assert(["native", "docs-derived", "curated"].includes(transition.provenance), `invalid transition provenance: ${transition.id}`);
}

for (const path of [
  ...domain.nodes.flatMap((node) => node.sources.decisions),
  ...domain.nodes.map((node) => node.sources.prototype),
  ...domain.nodes.map((node) => node.sources.screenshot).filter(Boolean)
]) {
  try {
    await access(join(repositoryRoot, path));
  } catch {
    failures.push(`missing repository evidence: ${path}`);
  }
}

for (const path of [
  "design/shared/pen/recipe-detail-first-map.pen",
  "design/shared/pen/exports/recipe-detail-first-map.png"
]) {
  try {
    await access(join(repositoryRoot, path));
  } catch {
    failures.push(`missing derived Pen artifact: ${path}`);
  }
}

assert(normalized.journeys.length === 3, "normalized input lost a journey");
assert(normalized.journeys.flatMap((journey) => journey.nodes).length === domain.nodes.length, "normalized input lost a node");
assert(normalized.warnings.some((warning) => warning.id === "warning.roadmap-pr80-state"), "roadmap contradiction must remain visible");
assert(normalized.warnings.some((warning) => warning.id === "warning.import-review-contract"), "Import review contradiction must remain visible");

if (failures.length) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.log(`Validated ${domain.nodes.length} nodes, ${domain.transitions.length} transitions, ${domain.warnings.length} warnings, and all repository evidence links.`);
