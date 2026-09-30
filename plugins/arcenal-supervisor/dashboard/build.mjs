import { build } from "esbuild";
import { copyFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

await build({
  bundle: true,
  entryPoints: [fileURLToPath(new URL("src/index.ts", import.meta.url))],
  format: "iife",
  logLevel: "info",
  minify: true,
  outfile: fileURLToPath(new URL("dist/index.js", import.meta.url)),
  target: ["es2022"],
});

await copyFile(
  fileURLToPath(new URL("src/style.css", import.meta.url)),
  fileURLToPath(new URL("dist/style.css", import.meta.url)),
);
