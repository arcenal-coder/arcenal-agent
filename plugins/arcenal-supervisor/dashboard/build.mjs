import { build } from "esbuild";
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
