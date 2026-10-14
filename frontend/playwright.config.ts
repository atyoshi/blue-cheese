import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8579",
    browserName: "chromium",
    timezoneId: "UTC",
    locale: "en-US",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.005, animations: "disabled" },
  },
  webServer: {
    command: "../.venv/bin/python tests/serve.py",
    url: "http://127.0.0.1:8579/health",
    reuseExistingServer: false,
    timeout: 20000,
  },
});
