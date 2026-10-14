import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { fileURLToPath } from "node:url";
const fixture = fileURLToPath(
  new URL("../../tests/fixtures/sample_eve.json", import.meta.url),
);
async function post(request: APIRequestContext, path: string, body: unknown) {
  const session = await request.get("/api/v1/session");
  const { csrf } = await session.json();
  const response = await request.post("/api/v1/" + path, {
    data: body,
    headers: { "x-csrf-token": csrf },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}
async function seed(request: APIRequestContext) {
  await post(request, "source", { action: "import", path: fixture });
}
async function completedCase(request: APIRequestContext) {
  await seed(request);
  let cases = await (await request.get("/api/v1/cases")).json();
  if (!cases.some((c: { status: string }) => c.status === "COMPLETED")) {
    const alerts = await (await request.get("/api/v1/alerts")).json();
    await post(request, "cases", {
      seed_event_id: alerts.groups[0].seed_ids[0],
    });
    await expect
      .poll(async () => {
        cases = await (await request.get("/api/v1/cases")).json();
        return cases.some((c: { status: string }) => c.status === "COMPLETED");
      })
      .toBeTruthy();
  }
  return cases.find((c: { status: string }) => c.status === "COMPLETED");
}
async function clean(page: Page) {
  for (const selector of ['.drawer[data-state="open"]', ".tab-content"])
    if (await page.locator(selector).count())
      await expect(page.locator(selector)).toHaveCSS("opacity", "1");
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
}
async function theme(page: Page, value: string) {
  await page.addInitScript(
    (t) => localStorage.setItem("bluecheese-theme", t),
    value,
  );
}

for (const mode of ["light", "dark"])
  for (const width of [390, 768, 1280, 1440]) {
    test(`alert queue ${mode} ${width}`, async ({ page, request }) => {
      await seed(request);
      await theme(page, mode);
      await page.setViewportSize({ width, height: 960 });
      await page.goto("/");
      await expect(
        page.getByRole("button", {
          name: "ET INFO TeamViewer Dyngate User-Agent",
          exact: true,
        }),
      ).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", mode);
      await clean(page);
      await expect(page).toHaveScreenshot(`alerts-${mode}-${width}.png`, {
        fullPage: true,
      });
      const before = await (await request.get("/api/v1/status")).json();
      await page
        .getByRole("button", { name: "Open ET INFO TeamViewer" })
        .click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await clean(page);
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toHaveCount(0);
      const after = await (await request.get("/api/v1/status")).json();
      expect(after.investigation_runs).toBe(before.investigation_runs);
    });
  }

test("real alert to decision journey, evidence, chat, exports and revisions", async ({
  page,
  request,
}) => {
  await seed(request);
  await theme(page, "dark");
  await page.setViewportSize({ width: 1440, height: 1000 });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Open ET INFO TeamViewer" }).click();
  await page.getByRole("button", { name: "Investigate", exact: true }).click();
  await expect(page).toHaveURL(/#cases\//);
  await expect(
    page.getByRole("heading", { name: "Assessment", exact: true }),
  ).toBeVisible();
  const runId = page.url().split("#cases/")[1];
  await clean(page);
  await page.getByRole("tab", { name: "Evidence", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Connections", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".connections-chart svg")).toBeVisible();
  await clean(page);
  await page
    .getByRole("button", { name: /Open evidence / })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".code")).toContainText("timestamp");
  await page.getByRole("tab", { name: "Normalized", exact: true }).click();
  await expect(page.locator(".code")).toContainText("src_ip");
  await clean(page);
  await page.keyboard.press("Escape");
  await page.getByRole("tab", { name: "Activity", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Agent operations" }),
  ).toBeVisible();
  await expect(page.locator(".operation-list li")).not.toHaveCount(0);
  await page.getByRole("tab", { name: "Decision", exact: true }).click();
  await page.getByLabel("Analyst", { exact: true }).fill("Morgan");
  await page.getByLabel("Assigned to", { exact: true }).fill("On call");
  await page
    .getByLabel("Disposition", { exact: true })
    .selectOption("ESCALATED");
  await page
    .getByLabel("Notes", { exact: true })
    .fill("Verify endpoint context.");
  await page.getByRole("button", { name: "Save decision" }).click();
  await expect(page.getByRole("status")).toContainText("Decision saved");
  await page.reload();
  await page.getByRole("tab", { name: "Decision", exact: true }).click();
  await expect(page.getByLabel("Assigned to", { exact: true })).toHaveValue(
    "On call",
  );
  await expect(page.locator(".decision-history")).toContainText("Morgan");
  await page
    .getByRole("button", { name: "Ask Blue Cheese", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Summarize this case");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".chat-message.assistant")).toBeVisible();
  await clean(page);
  const before = await (await request.get("/api/v1/status")).json();
  await page.getByRole("button", { name: "Refresh view", exact: true }).click();
  const after = await (await request.get("/api/v1/status")).json();
  expect(after.investigation_runs).toBe(before.investigation_runs);
  await page.getByRole("tab", { name: "Findings", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "JSON", exact: true }).click();
  expect((await download).suggestedFilename()).toBe(runId + ".json");
  await page.getByRole("button", { name: "New revision", exact: true }).click();
  await expect(page).not.toHaveURL(new RegExp(runId + "$"));
  expect(errors).toEqual([]);
});

test("settings, theme persistence, network selection and mobile chat", async ({
  page,
  request,
}) => {
  await page.goto("/#settings");
  await page.getByRole("button", { name: "Dark", exact: true }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("File path", { exact: true }).fill(fixture);
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Source connected");
  await page.getByRole("button", { name: "Disconnect", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Source disconnected");
  await clean(page);
  await page.goto("/#network");
  await expect(
    page.getByRole("heading", { name: "Activity over time" }),
  ).toBeVisible();
  await page.locator(".connections-chart [role=button]").first().click();
  await expect(
    page.getByRole("button", { name: "Clear connection", exact: true }),
  ).toBeVisible();
  await clean(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.locator("nav").getByRole("link", { name: "Cases" }).click();
  await page.locator(".row-title").first().click();
  await page
    .getByRole("button", { name: "Ask Blue Cheese", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await clean(page);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("contrast tokens cover text, controls, status colors and overlays in both themes", async ({
  page,
}) => {
  for (const mode of ["light", "dark"]) {
    await page.goto("/#settings");
    await page
      .getByRole("button", {
        name: mode === "light" ? "Light" : "Dark",
        exact: true,
      })
      .click();
    const ratios = await page.evaluate(() => {
      const css = getComputedStyle(document.documentElement);
      const value = (token: string) =>
        css.getPropertyValue("--" + token).trim();
      const lum = (hex: string) => {
        const full =
          hex.length === 4
            ? "#" + [...hex.slice(1)].map((c) => c + c).join("")
            : hex;
        const c = [1, 3, 5]
          .map((i) => parseInt(full.slice(i, i + 2), 16) / 255)
          .map((x) =>
            x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4,
          );
        return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722;
      };
      const ratio = (a: string, b: string) => {
        const [lo, hi] = [lum(value(a)), lum(value(b))].sort((a, b) => a - b);
        return (hi + 0.05) / (lo + 0.05);
      };
      return {
        text: ratio("text", "bg"),
        secondary: ratio("muted", "surface-raised"),
        button: ratio("on-accent", "accent"),
        danger: ratio("danger", "danger-soft"),
        warning: ratio("warning", "warning-soft"),
        success: ratio("success", "success-soft"),
        control: ratio("control-border", "surface"),
        chart: ratio("flow", "surface"),
        chartAlert: ratio("chart-alert", "surface"),
      };
    });
    expect(ratios.text).toBeGreaterThanOrEqual(7);
    expect(ratios.secondary).toBeGreaterThanOrEqual(7);
    for (const key of ["button", "danger", "warning", "success"])
      expect(ratios[key as keyof typeof ratios], key).toBeGreaterThanOrEqual(
        4.5,
      );
    for (const key of ["control", "chart", "chartAlert"])
      expect(ratios[key as keyof typeof ratios], key).toBeGreaterThanOrEqual(3);
    await clean(page);
  }
});

for (const mode of ["light", "dark"])
  test(`case layout and tooltip ${mode}`, async ({ page, request }) => {
    await seed(request);
    await theme(page, mode);
    await page.setViewportSize({ width: 1440, height: 1000 });
    const alerts = await (await request.get("/api/v1/alerts")).json();
    await post(request, "cases", {
      seed_event_id: alerts.groups[0].seed_ids[0],
    });
    await expect
      .poll(async () => {
        const list = await (await request.get("/api/v1/cases")).json();
        return list[0]?.status;
      })
      .toBe("COMPLETED");
    const cases = await (await request.get("/api/v1/cases")).json();
    await page.goto("/#cases/" + cases[0].run_id);
    await expect(
      page.getByRole("heading", { name: "Assessment", exact: true }),
    ).toBeVisible();
    await clean(page);
    await expect(page).toHaveScreenshot(`case-${mode}.png`, {
      fullPage: true,
      maskColor: mode === "dark" ? "#343d4a" : "#d9dfe7",
      mask: [
        page.locator(".eyebrow .mono"),
        page.locator(".scope-strip>div:nth-child(3) strong"),
        page.locator(".case-header-meta>span:last-child"),
      ],
    });
    await page
      .getByRole("button", { name: "Refresh view", exact: true })
      .hover();
    await expect(page.getByRole("tooltip")).toBeVisible();
    await expect(page.getByRole("tooltip")).toHaveCSS("opacity", "1");
    await clean(page);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page
      .getByRole("button", { name: "Ask Blue Cheese", exact: true })
      .click();
    await expect(page.locator(".chat-panel")).toBeVisible();
    await clean(page);
    await page.goto("/#network");
    await expect(
      page.getByRole("heading", { name: "Connections", exact: true }),
    ).toBeVisible();
    await clean(page);
    await expect(page).toHaveScreenshot(`network-${mode}.png`, {
      fullPage: true,
    });
  });

test("long labels, IPv6, narrow drawers, unsaved decisions and 200 percent layout", async ({
  page,
  request,
}) => {
  await seed(request);
  await page.route("**/api/v1/alerts?*", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.groups[0].seed.normalized.alert_signature =
      "NetworkDetection".repeat(25) + " <script>alert(1)</script>";
    data.groups[0].seed.normalized.src_ip =
      "2001:db8:1234:5678:abcd:abcd:abcd:abcd";
    data.groups[0].seed.normalized.dest_ip =
      "2001:db8:4321:8765:dcba:dcba:dcba:dcba";
    await route.fulfill({ response, json: data });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".row-title")).toContainText("<script>");
  await clean(page);
  await page.locator(".row-title").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".detail-title")).toContainText("<script>");
  await clean(page);
  expect(
    await page
      .locator(".drawer")
      .evaluate((e) => e.scrollWidth <= e.clientWidth),
  ).toBeTruthy();
  await page.keyboard.press("Escape");
  const cases = await (await request.get("/api/v1/cases")).json();
  await page.goto("/#cases/" + cases[0].run_id);
  await page.getByRole("tab", { name: "Decision", exact: true }).click();
  await page.getByLabel("Analyst", { exact: true }).fill("Unsaved analyst");
  await page.getByLabel("Notes", { exact: true }).fill("Unsaved note");
  await page.getByRole("tab", { name: "Evidence", exact: true }).click();
  await page.getByRole("tab", { name: "Decision", exact: true }).click();
  await expect(page.getByLabel("Notes", { exact: true })).toHaveValue(
    "Unsaved note",
  );
  await page.getByRole("button", { name: "Refresh view", exact: true }).click();
  await expect(page.getByLabel("Analyst", { exact: true })).toHaveValue(
    "Unsaved analyst",
  );
  await page.setViewportSize({ width: 720, height: 500 });
  await clean(page);
  await page.getByRole("tab", { name: "Evidence", exact: true }).click();
  await clean(page);
});

test("case guidance and deterministic chat remain readable and case-specific", async ({
  page,
  request,
}) => {
  await seed(request);
  await page.setViewportSize({ width: 1280, height: 960 });
  const savedCase = await completedCase(request);
  await page.goto("/#cases/" + savedCase.run_id);
  await expect(
    page.getByRole("heading", { name: "Assessment", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Unknowns", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".shared-guidance")).toHaveCount(1);
  await expect(page.locator(".shared-guidance")).not.toHaveAttribute("open");
  await expect(
    page.getByText("Evidence window", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ask Blue Cheese", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Summarize this case", exact: true })
    .click();
  const reply = page.locator(".chat-message.assistant").last();
  await expect(reply.locator(".readable-prose p").first()).toBeVisible();
  await expect(reply.locator(".readable-prose li").first()).toBeVisible();
  await expect(reply).not.toContainText("logs.;");
  await expect(reply).not.toContainText("An alert is a sensor rule match");
  await expect(reply).not.toContainText("Coverage: at most");
  await expect(reply.locator(".code")).toHaveCount(0);
  await clean(page);
  await expect(page).toHaveScreenshot("readable-case-chat.png", {
    fullPage: true,
  });
});

test("structured model answers render safe paragraphs and lists in narrow chat", async ({
  page,
  request,
}) => {
  await seed(request);
  const savedCase = await completedCase(request);
  const runId = savedCase.run_id;
  await page.route("**/api/v1/chat?run_id=*", async (route) => {
    await route.fulfill({
      json: {
        pending: false,
        messages: [
          {
            role: "user",
            content: "What should I check next?",
            created_at: "2026-10-14T12:00:00Z",
          },
          {
            role: "assistant",
            created_at: "2026-10-14T12:00:01Z",
            content: JSON.stringify({
              reply: "Compatibility text",
              action: "answer",
              citations: [],
              blocks: [
                {
                  title: "",
                  kind: "paragraph",
                  items: [
                    "The selected connection needs an authorization check.",
                  ],
                },
                {
                  title: "Next checks",
                  kind: "bullets",
                  items: [
                    "Confirm the endpoint owner's task at the observed time.",
                    "Treat <img src=x onerror=alert(1)> as literal evidence text.",
                  ],
                },
              ],
            }),
          },
        ],
      },
    });
  });
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/#cases/" + runId);
  await page
    .getByRole("button", { name: "Ask Blue Cheese", exact: true })
    .click();
  const answer = page.locator(".chat-message.assistant");
  await expect(answer.locator(".readable-prose p")).toHaveCount(1);
  await expect(answer.getByRole("listitem")).toHaveCount(2);
  await expect(answer.locator("img")).toHaveCount(0);
  await expect(answer).not.toContainText("Compatibility text");
  await clean(page);
  await expect(page).toHaveScreenshot("readable-narrow-model-chat.png", {
    fullPage: true,
  });
});

test("failed cases expose readable request diagnostics without creating work", async ({
  page,
  request,
}) => {
  await seed(request);
  const savedCase = await completedCase(request);
  const saved = await (
    await request.get("/api/v1/cases/" + savedCase.run_id)
  ).json();
  const diagnostic = {
    turns: [
      {
        operation_id: "model-3",
        role: "Investigator",
        model: "configured-model",
        status: "ERROR",
        outcome: "TIMEOUT",
        duration_seconds: 300,
        usage: { completion_tokens: null },
      },
    ],
  };
  const events = [
    {
      sequence: 1,
      role: "Investigator",
      status: "failed",
      kind: "model",
      message: "Model request did not complete.",
      elapsed_seconds: 300,
      outcome: "TIMEOUT",
    },
  ];
  await page.route("**/api/v1/cases/" + saved.run_id, (route) =>
    route.fulfill({
      json: {
        ...saved,
        report: null,
        status: "FAILED",
        error: "The model request timed out after 300 seconds.",
        provider_diagnostics: diagnostic,
      },
    }),
  );
  await page.route("**/api/v1/cases/" + saved.run_id + "/activity", (route) =>
    route.fulfill({
      json: {
        status: "FAILED",
        events,
        elapsed_seconds: 300,
        provider_diagnostics: diagnostic,
      },
    }),
  );
  const before = await (await request.get("/api/v1/status")).json();
  await page.goto("/#cases/" + saved.run_id);
  await expect(
    page.getByText("The model request timed out after 300 seconds.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "View activity", exact: true })
    .click();
  await page.getByText("Model request diagnostics", { exact: true }).click();
  await expect(
    page.getByRole("cell", { name: "300.0s", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Timeout", exact: true }),
  ).toBeVisible();
  await clean(page);
  const after = await (await request.get("/api/v1/status")).json();
  expect(after.investigation_runs).toBe(before.investigation_runs);
});
