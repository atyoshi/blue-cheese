import { readdir, readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";
const dir = new URL(
  "../../src/bluecheese/interfaces/static/assets/",
  import.meta.url,
);
const files = (await readdir(dir)).filter((f) => f.endsWith(".js"));
const index = files.find((f) => f.startsWith("index-"));
const bytes = gzipSync(await readFile(new URL(index, dir))).length;
console.log(
  `Initial JavaScript: ${(bytes / 1024).toFixed(1)} KiB gzip (budget: 200 KiB)`,
);
if (bytes > 200 * 1024) process.exit(1);
