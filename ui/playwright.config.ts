// One smoke spec (ARCHITECTURE.md §9) against the real backend serving ui/dist (run `npm run build` first).
import { defineConfig } from "@playwright/test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const port = 8123;
// a settings file of the tests' own: the first run is over, so the app does not open the guided setup by
// itself (the "Get started" test fakes a first run)
const settings = join(mkdtempSync(join(tmpdir(), "effigy-settings-")), "settings.json");
writeFileSync(settings, JSON.stringify({ welcomed: true }));

export default defineConfig({
  testDir: "tests", // inside ui/ so @playwright/test resolves from ui/node_modules
  timeout: 60_000,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    launchOptions: {
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"], // WebGL without a GPU
      executablePath: process.env.PW_CHROMIUM, // a preinstalled Chromium, if the bundled one is missing
    },
  },
  webServer: {
    command: `uv run uvicorn server.app:app --port ${port}`,
    cwd: "..",
    env: { EFFIGY_LIBRARY: mkdtempSync(join(tmpdir(), "effigy-ui-")), EFFIGY_SETTINGS: settings },
    url: `http://127.0.0.1:${port}/api/health`,
  },
});
