// Screenshots of the design preview. Usage: node preview/shots.cjs [filter]
// Needs the preview server running: npx vite --config preview/vite.config.ts
const path = require("path");
const { chromium } = require(path.join(require("child_process").execSync("npm root -g").toString().trim(), "playwright"));

const BASE = "http://localhost:1430/";
const OUT = path.join(__dirname, "shots");
const SHOTS = [
  { name: "01-today-ops", q: "?as=ops" },
  { name: "02-today-admin", q: "?as=admin" },
  { name: "03-team-gm", q: "?as=gm", nav: "Team Today" },
  { name: "04-owner", q: "?as=owner", nav: "Owner Overview" },
  { name: "05-work", q: "?as=ops", nav: "My Work" },
  { name: "06-training", q: "?as=ops", nav: "My Training" },
  { name: "07-inbox", q: "?as=gm", nav: "Exceptions" },
  { name: "08-onboarding", q: "?as=admin&first=1" },
  { name: "09-signed-out", q: "?state=signed_out" },
  { name: "10-guide", q: "?as=ops&mode=guide_dock", w: 380 },
  { name: "11-guide-offtrack", q: "?as=ops&mode=guide_dock&guide=off_track", w: 380 },
  { name: "12-toolbar-odoo", q: "?as=ops&mode=odoo", h: 48 },
];

(async () => {
  const filter = process.argv[2];
  require("fs").mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  for (const s of SHOTS.filter((s) => !filter || s.name.includes(filter))) {
    const page = await browser.newPage({ viewport: { width: s.w || 1280, height: s.h || 860 }, deviceScaleFactor: 1 });
    await page.goto(BASE + s.q);
    await page.waitForTimeout(900);
    if (s.nav) {
      await page.getByRole("navigation", { name: "DeployGuard sections" }).getByText(s.nav, { exact: true }).click();
      await page.waitForTimeout(900);
    }
    await page.screenshot({ path: path.join(OUT, s.name + ".png") });
    await page.close();
    console.log("shot", s.name);
  }
  await browser.close();
})();
