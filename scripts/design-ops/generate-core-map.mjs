import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeCoreMap, readCoreMapSources } from "./core-map-normalizer.mjs";

const repositoryRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const outputPath = join(repositoryRoot, "design", "shared", "pen", "inputs", "recipe-detail-core-map.json");

const sources = await readCoreMapSources(repositoryRoot);
const normalized = normalizeCoreMap(sources);

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(normalized, null, 2)}\n`, "utf8");
console.log(`Generated ${outputPath}`);
