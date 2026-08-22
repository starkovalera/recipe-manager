import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const graphRoot = join(repositoryRoot, "design", "shared", "design-graph");
const outputPath = join(repositoryRoot, "design", "shared", "pen", "inputs", "recipe-detail-core-map.json");

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));
const graph = await readJson(join(graphRoot, "graph.json"));
const domain = await readJson(join(graphRoot, graph.domains[0].source));
const github = await readJson(join(graphRoot, graph.snapshots[0].source));

if (domain.iteration !== "core") {
  throw new Error(`Expected the active domain to be the Core map, got ${domain.iteration ?? "unknown"}`);
}

const issueByNumber = new Map(github.issues.map((issue) => [issue.number, issue]));
const pullRequestByNumber = new Map(github.pullRequests.map((pullRequest) => [pullRequest.number, pullRequest]));

const normalizeSources = (sources) => ({
  ...sources,
  issues: sources.issues.map((number) => issueByNumber.get(number)),
  pullRequests: sources.pullRequests.map((number) => pullRequestByNumber.get(number))
});

const normalized = {
  schemaVersion: graph.schemaVersion,
  generatedFrom: {
    domain: graph.domains[0].source,
    githubSnapshot: graph.snapshots[0].source,
    asOf: github.asOf,
    sourceRevision: github.sourceRevision,
    precedence: graph.precedence
  },
  map: {
    id: domain.id,
    title: domain.title,
    iteration: domain.iteration,
    platform: domain.platform,
    release: domain.release,
    issue: domain.issue,
    predecessor: domain.predecessor,
    parallelWork: domain.parallelWork,
    joinWork: domain.joinWork,
    setupProvenance: domain.setupProvenance
  },
  journeys: [...domain.journeys]
    .sort((left, right) => left.order - right.order)
    .map((journey) => ({
      ...journey,
      nodes: domain.nodes
        .filter((node) => node.journeyId === journey.id)
        .sort((left, right) => left.order - right.order)
        .map((node) => ({
          ...node,
          sources: normalizeSources(node.sources)
        }))
    })),
  reviewSelection: [...domain.reviewSelection],
  placeholderNodes: [...domain.placeholderNodes],
  transitions: [...domain.transitions].sort((left, right) => left.id.localeCompare(right.id)),
  warnings: [...domain.warnings].sort((left, right) => left.id.localeCompare(right.id))
};

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(normalized, null, 2)}\n`, "utf8");
console.log(`Generated ${outputPath}`);
