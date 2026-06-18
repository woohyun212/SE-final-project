/**
 * capture.js — Electron screenshot driver for the PPT deck.
 *
 * Launches a real Electron window against the running Next dev server
 * (http://localhost:3000, which is built to call the live backend), walks
 * through the full product flow with a fake microphone fed by a Korean WAV,
 * and saves a PNG of every screen.
 *
 * Run with:  npx electron screenshots/capture.js
 *
 * Fake mic: Chromium switches make getUserMedia() return our WAV as a virtual
 * microphone, so the real record -> POST /recommend -> recommend page flow runs
 * end to end without a physical mic.
 */
const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:3000';
const OUT_DIR = __dirname;
const WAV = path.join(__dirname, 'voice_sample.wav');

// A unique account per run so signup never collides ("already in use").
const STAMP = process.env.RUN_STAMP || 'demo';
const EMAIL = `demo+${STAMP}@example.com`;
const PASSWORD = 'demoPass123';

// ── Fake audio: feed the WAV as a virtual microphone ─────────────────────────
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('use-file-for-fake-audio-capture', WAV);
// Auto-grant the getUserMedia permission prompt.
app.commandLine.appendSwitch('use-fake-ui-for-media-stream');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Log to a file so we get full visibility regardless of stdout buffering.
const LOG = path.join(__dirname, 'capture.log');
fs.writeFileSync(LOG, '');
const _stdout = console.log.bind(console);
function log(...a) {
  const line = a.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
  fs.appendFileSync(LOG, line + '\n');
  _stdout(line);
}
console.log = log;

process.on('unhandledRejection', (e) =>
  log('[unhandledRejection]', (e && e.message) || String(e)));
process.on('uncaughtException', (e) =>
  log('[uncaughtException]', (e && e.message) || String(e)));

let win;

async function shot(name) {
  // Give fonts/layout a beat to settle before capturing.
  await sleep(600);
  const img = await win.webContents.capturePage();
  const file = path.join(OUT_DIR, `${name}.png`);
  fs.writeFileSync(file, img.toPNG());
  console.log(`[shot] ${file}`);
}

/** Navigate to an absolute app URL and wait for the load to finish. */
async function go(urlPath) {
  await win.loadURL(`${BASE}${urlPath}`);
  await sleep(1200); // let client-side hydration + guards run
}

/** Run JS in the page and return the result. */
const evalJs = (code) => win.webContents.executeJavaScript(code, true);

/** Run a named step; log and swallow errors so one failure doesn't abort the run. */
async function step(name, fn) {
  try {
    await fn();
    console.log(`[step ok] ${name}`);
  } catch (e) {
    console.log(`[step FAIL] ${name}: ${e && e.message}`);
  }
}

async function main() {
  win = new BrowserWindow({
    width: 1200,
    height: 900,
    show: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });

  // Grant media permission inside Electron too (belt and suspenders).
  win.webContents.session.setPermissionRequestHandler((_wc, _perm, cb) => cb(true));
  win.webContents.session.setPermissionCheckHandler(() => true);

  const fillForm = (fields) => evalJs(`(() => {
    const set = (sel, val) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const proto = Object.getPrototypeOf(el);
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(el, val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };
    const f = ${JSON.stringify(fields)};
    return Object.entries(f).every(([sel, val]) => set(sel, val));
  })()`);

  const hasToken = () =>
    evalJs(`!!localStorage.getItem('se_emotion_music__access_token')`);

  // Start from a clean, logged-out state so the auth screens render.
  await go('/login/');
  await evalJs(`localStorage.clear(); sessionStorage.clear();`);

  // ── 1. Signup ──────────────────────────────────────────────────────────────
  await step('signup', async () => {
    await go('/signup/');
    await shot('01-signup');
    const ok = await fillForm({
      '#email': EMAIL, '#password': PASSWORD, '#passwordConfirm': PASSWORD,
    });
    console.log('[signup] filled:', ok);
    await shot('02-signup-filled');
    await evalJs(`document.querySelector('form')?.requestSubmit()`);
    await sleep(3000);
    console.log('[signup] token after submit:', await hasToken(),
      'path:', await evalJs(`location.pathname`));
  });

  // ── 2. Login ─────────────────────────────────────────────────────────────────
  // Log out first so the login form is shown, then log in with the real account.
  await step('login', async () => {
    await go('/login/');
    await evalJs(`localStorage.clear(); sessionStorage.clear();`);
    await go('/login/');
    await shot('03-login');
    await fillForm({ '#email': EMAIL, '#password': PASSWORD });
    await shot('04-login-filled');
    await evalJs(`document.querySelector('form')?.requestSubmit()`);
    await sleep(3000);
    console.log('[login] token after submit:', await hasToken(),
      'path:', await evalJs(`location.pathname`));
  });

  // ── 3. Home (voice capture) → recommend ──────────────────────────────────────
  await step('home+recommend', async () => {
    await go('/');
    await sleep(1500); // auth guard may redirect; give it time
    console.log('[nav] after / ->', await evalJs(`location.pathname`),
      'token:', await hasToken());
    await shot('05-home-idle');

    // Start recording. The 5s auto-stop + fake WAV drives the real flow.
    await evalJs(`
      [...document.querySelectorAll('button')]
        .find(b => b.textContent.includes('녹음 시작'))?.click()
    `);
    await sleep(1500);
    await shot('06-home-recording');

    // Wait through the 5s recording window + upload + emotion analysis.
    // The page navigates to /recommend on success (handleResult).
    let landed = false;
    let analyzingShot = false;
    for (let i = 0; i < 45; i++) {
      await sleep(1000);
      const p = await evalJs(`location.pathname`);
      // Capture the "분석 중" spinner state once it appears.
      if (!analyzingShot) {
        const analyzing = await evalJs(
          `document.body.innerText.includes('분석하고 음악을 찾는')`
        );
        if (analyzing) { await shot('07-home-analyzing'); analyzingShot = true; }
      }
      if (p.includes('recommend')) { landed = true; break; }
    }
    console.log('[flow] landed on recommend:', landed);
    await sleep(3000); // let track list + chart + reasons render
    await shot('08-recommend');
    await captureFullPage('08b-recommend-full');
  });

  // ── 4. History ───────────────────────────────────────────────────────────────
  await step('history', async () => {
    await go('/history/');
    await sleep(3000); // GET /history round-trip
    await shot('09-history');
    await captureFullPage('09b-history-full');
  });

  console.log('[done] all screenshots captured');
  await sleep(500);
  app.quit();
}

/** Resize the window to the full page height and capture, then restore. */
async function captureFullPage(name) {
  try {
    const h = await evalJs(`Math.max(
      document.body.scrollHeight, document.documentElement.scrollHeight)`);
    const clamped = Math.min(Math.max(h, 900), 4000);
    const [w] = win.getSize();
    win.setSize(w, clamped);
    await sleep(800);
    const img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(OUT_DIR, `${name}.png`), img.toPNG());
    console.log(`[shot] ${name} (full ${clamped}px)`);
    win.setSize(w, 900);
  } catch (e) {
    console.log('[fullpage] failed:', e.message);
  }
}

let done = false;
app.whenReady().then(() => {
  main()
    .catch((err) => log('[fatal]', (err && err.message) || String(err)))
    .finally(() => { done = true; app.quit(); });
});

// Only let the app exit once main() has finished — guards against a transient
// window close mid-flow tearing the whole run down.
app.on('window-all-closed', (e) => { if (!done) e.preventDefault?.(); });
