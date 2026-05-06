import { Composio } from "@composio/core";
import { writeFile } from "fs/promises";

const composio = new Composio();

const tools = await composio.tools.getRawComposioTools({
  toolkits: ["github"],
  limit: 1000,
});

await writeFile(
  "github_tools.json",
  JSON.stringify(tools, null, 2),
  "utf-8"
);
console.log(`GitHub tools written: ${tools.length}`);
