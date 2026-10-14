// Run from any directory: node docs/ux-review/2026-10-12/evidence/browser-review.mjs
// UI-only evidence: every API/files request is fulfilled with fixtures; no backend or GPU job.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(dir, '../../../..');
const { createServer } = await import(pathToFileURL(join(root, 'ui/node_modules/vite/dist/node/index.js')));
const { chromium } = await import(pathToFileURL(join(root, 'ui/node_modules/playwright/index.mjs')));
const shots = join(dir, 'screenshots');
mkdirSync(shots, { recursive: true });
const GLB = readFileSync(join(root, 'tests/fixtures/two_tris.glb'));
const ANIM = readFileSync(join(root, 'tests/fixtures/anim.glb'));
const PNG = readFileSync(join(root, 'tests/fixtures/golden/lantern.png'));
const when = '2026-10-12T10:00:00Z';
const meta = (version, step, parent, outputs, extras = {}) => ({ version, step, parent, outputs, created: when, params: {}, metrics: {}, provenance: 'step', restricted: false, ...extras });
const versions = [
  meta('001_upload', 'upload', null, { image: 'reference.png' }),
  meta('002_brief', 'brief', null, { brief: 'brief.json' }, { params: { prompt: 'A worn brass lantern for a stylized adventure game', category: 'prop' } }),
  meta('003_concepts', 'concepts', '002_brief', { cand_0: 'candidate_0.png', cand_1: 'candidate_1.png', cand_2: 'candidate_2.png', cand_3: 'candidate_3.png', scores: 'scores.json' }),
  meta('004_prep', 'prep', '003_concepts', { image: 'image.png' }, { params: { pick: 0 } }),
  meta('005_trellis2', 'trellis2', '004_prep', { mesh: 'mesh.glb', ovoxel: 'ovoxel.npz' }, { params: { weights: 'faithful' } }),
  meta('006_clean', 'clean', '005_trellis2', { mesh: 'mesh.glb' }),
  meta('007_remesh', 'remesh', '006_clean', { mesh: 'mesh.glb' }, { params: { faces: 10000 } }),
  meta('008_uv', 'uv', '007_remesh', { mesh: 'mesh.glb' }),
  meta('009_bake', 'bake', '008_uv', { mesh: 'mesh.glb' }, { licenses: ['Fixture/faithful'] }),
  meta('010_validate', 'validate', '009_bake', { checklist: 'checklist.json' }, { metrics: { fail: 0 } }),
  meta('011_export', 'export', '009_bake', { model: 'lantern.obj', materials: 'lantern.mtl', albedo: 'albedo.png', credits: 'CREDITS.txt', licenses: 'LICENSES.json' }, { metrics: { profile: 'obj' } }),
  meta('012_import_model', 'import_model', null, { mesh: 'mesh.glb' }, { metrics: { format: '.glb', height_m: 1.8, triangles: 10000, materials: 2, textures: 3 } }),
  meta('013_rig_skin', 'rig_skin', '009_bake', { rigged: 'rigged.glb', skeleton: 'skeleton.json', qa: 'qa.json' }),
  meta('014_anim', 'anim', '013_rig_skin', { rigged_anim: 'rigged_anim.glb', skeleton: 'skeleton.json', clips: 'clips.json' }),
];
const assets = Array.from({ length: 8 }, (_, i) => ({ id: i ? `fixture_${i}` : 'ux_fixture', name: i === 7 ? 'A very long asset name for examining line wrapping in the card and workspace' : ['Brass lantern', 'Forest creature', 'Stone arch', 'Helmet', 'Chair', 'Brass lantern', 'Dragon'][i], created: when, updated: when, tags: [i % 2 ? 'character' : 'prop'], versions: 14 }));
const groups = ['concepts', 'faithful', 'fast', 'texture', 'refine', 'parts', 'kimodo', 'mocap'];
const models = groups.map((g, i) => ({ id: i, name: g === 'faithful' ? 'facebook/dinov3-fixture' : `Fixture/${g}`, groups: [g], where: g, installed: true, partial: false, bytes: 2e9, missing_bytes: 0, revision: 'fixture' }));
const steps = { trellis2: { faithful: { op: 'generate', weights: 'faithful', resolution: 1024 }, fast: { op: 'generate', weights: 'fast', resolution: 512 } }, validate: { default: {} }, clean: { default: {} }, bake: { default: {} } };
const observations = { baseline: '06be15b87798128a6ed1024c2f1f19d5c2aa8946', isolation: 'Vite port 8147; mocked API/files/EventSource; installed Playwright; synthetic meshes and lantern image; no backend', captures: [], probes: [], errors: [] };
const save = () => writeFileSync(join(dir, 'observations.json'), JSON.stringify(observations, null, 2));
let server, browser;
async function setup(viewport = { width: 1440, height: 900 }) {
  const context = await browser.newContext({ viewport });
  await context.addInitScript(() => {
    class FakeSource {
      readyState = 1; handlers = new Map();
      constructor() { window.uxSource = this; }
      addEventListener(n, f) { const xs = this.handlers.get(n) ?? []; xs.push(f); this.handlers.set(n, xs); }
      emit(n, d = {}) { this.readyState = n === 'error' ? 0 : 1; for (const f of this.handlers.get(n) ?? []) f({ data: JSON.stringify(d) }); }
      close() {}
    }
    window.EventSource = FakeSource;
  });
  const page = await context.newPage();
  page.setDefaultTimeout(7000);
  page.on('pageerror', e => observations.errors.push(e.message));
  const state = { empty: false, missing: false, posts: [], failSave: false, serverVersions: [...versions] };
  await page.route('**/api/**', async r => {
    const path = new URL(r.request().url()).pathname;
    const method = r.request().method();
    if (/\/api\/assets\/[^/]+\/(thumb|turntable)$/.test(path)) return r.fulfill({ body: PNG, contentType: 'image/png' });
    if (method !== 'GET') {
      state.posts.push({ path, method, body: r.request().postDataJSON() });
      if (state.failSave) return r.fulfill({ status: 400, json: { error: { code: 'bad_params', message: 'Fixture save refused' } } });
      return r.fulfill({ status: 400, json: { error: { code: 'fixture_only', message: 'Computation is not part of this visual review' } } });
    }
    let json;
    if (path === '/api/assets') json = state.empty ? [] : assets;
    else if (/^\/api\/assets\/[^/]+$/.test(path)) json = { asset: assets.find(a => path.endsWith(a.id)) ?? assets[0], versions: state.serverVersions };
    else if (path === '/api/steps') json = steps;
    else if (path === '/api/models') json = models.map(m => ({ ...m, installed: !state.missing, bytes: state.missing ? 0 : m.bytes, missing_bytes: state.missing ? 2e9 : 0 }));
    else if (path === '/api/models/sizes') json = Object.fromEntries(groups.map(g => [g, 2e9]));
    else if (path === '/api/environments') json = [{ name: '.venv-ml', state: 'ok', groups }];
    else if (path === '/api/setup/first-run') json = { first_run: false };
    else if (path === '/api/setup/machine') json = [{ id: 'gpu', label: 'NVIDIA RTX 5080 Laptop', detail: '16 GB video memory', level: 'ok', budget_gb: 15 }, { id: 'ram', label: '32 GB RAM', detail: 'Enough memory', level: 'ok' }, { id: 'blender', label: 'Blender available', detail: 'Fixture reading', level: 'ok' }];
    else if (path === '/api/setup/folder') json = { path: 'D:\\Effigy\\models', source: 'default', bytes: 0, choices: [{ path: 'D:\\Effigy\\models', drive: 'D:', free: 240e9, total: 1e12 }, { path: 'E:\\Effigy-models', drive: 'E:', free: 600e9, total: 1e12 }] };
    else if (path === '/api/setup/presets') json = ['props', 'characters', 'motion', 'all'].map((id, i) => ({ id, name: ['Props', 'Characters', 'Characters with motion', 'Everything'][i], what: ['Pictures and static 3D models', 'Pictures, models and character rigs', 'Character rigs with text and video motion', 'Every available feature'][i], groups: groups.slice(0, i + 2), bytes: (i + 1) * 30e9, missing: (i + 1) * 30e9 }));
    else if (path === '/api/hf') json = { token: false, user: null, access: {}, gated: { 'facebook/dinov3': ['faithful'], 'meta-llama/Meta-Llama-3-8B-Instruct': ['kimodo'] } };
    else if (path === '/api/storage') json = { scanned: Date.now(), items: [], assets: [], drives: [{ drive: 'D:', total: 1e12, free: 240e9, low: false }] };
    else if (path === '/api/storage/drives') json = [{ drive: 'D:', total: 1e12, free: 240e9, low: false }];
    else if (path === '/api/blender/status') json = { link: null };
    else if (path === '/api/clips') json = ['Idle_A', 'Jog', 'Walk', 'Wave'].map(name => ({ name, file: name + '.fbx' }));
    else if (path === '/api/licenses') json = [{ name: 'Fixture/faithful', kind: 'model', license: 'MIT', commercial: true }];
    else if (path === '/api/agent/setup') json = { root: 'D:\\Effigy', server: 'mcp/effigy_server.py', uv: 'uv', clients: [{ id: 'codex', name: 'Codex', how: 'Paste into your agent configuration.', text: 'Fixture configuration; no connection made.' }] };
    else json = [];
    return r.fulfill({ json });
  });
  await page.route('**/files/**', async r => {
    const path = new URL(r.request().url()).pathname;
    if (/\.glb$/.test(path)) return r.fulfill({ body: /rigged/.test(path) ? ANIM : GLB, contentType: 'model/gltf-binary' });
    if (/\.(png|webp|jpg)$/.test(path)) return r.fulfill({ body: PNG, contentType: 'image/png' });
    const json = path.endsWith('scores.json') ? Object.fromEntries([0, 1, 2, 3].map(i => [`candidate_${i}.png`, { rank: i + 1, gates: {} }]))
      : path.endsWith('brief.json') ? { prompt: 'A worn brass lantern for a stylized adventure game', category: 'prop' }
      : path.endsWith('clips.json') ? { clips: [{ name: 'Idle', seconds: .5, frames: 12 }, { name: 'Walk', seconds: 1, frames: 24 }], fps: 24, missing: [] }
      : path.endsWith('skeleton.json') ? { template: 'mixamo52', joints: [{ name: 'Hips', parent: null, position: [0, 1, 0] }, { name: 'Spine', parent: 'Hips', position: [0, 1.2, 0] }] }
      : path.endsWith('qa.json') ? { items: {}, picked: 'import' }
      : path.endsWith('checklist.json') ? { items: { triangle_budget: { status: 'pass', value: 9842 }, has_uvs: { status: 'pass', value: true }, watertight: { status: 'warn', value: 2 }, uv_overlap: { status: 'warn', value: 2.1 } } }
      : {};
    return r.fulfill({ json });
  });
  return { page, context, state };
}
async function go(page, hash) {
  await page.goto('http://127.0.0.1:8147/' + hash);
  await page.reload(); // hash-only navigation otherwise carries open drawers between screenshots
  await page.locator('main').waitFor();
  if (hash.includes('/asset')) await page.locator('.workspace').waitFor();
  await page.waitForTimeout(250);
}
async function capture(page, name, fullPage = false) {
  const path = `screenshots/${name}.png`;
  await page.screenshot({ path: join(dir, path), fullPage });
  const measured = await page.evaluate(() => {
    const rect = el => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) }; };
    const visible = el => el.checkVisibility();
    const panel = document.querySelector('.panel');
    const preview = document.querySelector('.preview');
    return {
      viewport: { width: innerWidth, height: innerHeight }, documentWidth: document.documentElement.scrollWidth,
      stages: [...document.querySelectorAll('.stages button')].map(b => ({ text: b.textContent.trim(), disabled: b.disabled, rect: rect(b) })),
      panel: panel ? { ...rect(panel), scrollHeight: panel.scrollHeight, scrollWidth: panel.scrollWidth, clientHeight: panel.clientHeight, sections: [...panel.querySelectorAll('h3')].map(x => x.textContent) } : null,
      preview: preview ? rect(preview) : null,
      primary: [...document.querySelectorAll('.primary')].filter(visible).map(b => ({ text: b.textContent.trim(), rect: rect(b), disabled: b.disabled ?? false })),
      bodyText: document.querySelector('main').innerText,
    };
  });
  observations.captures.push({ name, path, ...measured }); save(); console.log(JSON.stringify({ capture: name, panel: measured.panel, primary: measured.primary }));
}
async function probe(name, fn) {
  try { const result = await fn(); observations.probes.push({ name, ...result }); console.log(JSON.stringify({ probe: name, ...result })); }
  catch (e) { observations.probes.push({ name, probeError: String(e) }); console.log(JSON.stringify({ probe: name, error: String(e) })); }
  save();
}
try {
  server = await createServer({ root: join(root, 'ui'), configFile: false, logLevel: 'error', server: { host: '127.0.0.1', port: 8147, strictPort: true } });
  await server.listen();
  browser = await chromium.launch({ headless: true, executablePath: process.env.PW_CHROMIUM || chromium.executablePath(), args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const { page, context, state } = await setup();
  for (const [name, hash] of [['library', '#/library'], ['new-description', '#/new'], ['import', '#/import'], ['setup', '#/setup']]) { await go(page, hash); await capture(page, name, name === 'setup'); }
  state.missing = true; await go(page, '#/welcome'); await capture(page, 'welcome', true); state.missing = false;
  await go(page, '#/new'); await page.getByRole('button', { name: 'From an image', exact: true }).click(); await capture(page, 'new-image');
  for (const [name, v] of [['concepts', '003_concepts'], ['reference-generate', '004_prep'], ['generated-prepare', '005_trellis2'], ['textured-bake', '009_bake'], ['checked-model', '010_validate'], ['export-obj', '011_export'], ['imported-model', '012_import_model'], ['skin-animation-options', '013_rig_skin'], ['animated-model', '014_anim']]) { await go(page, `#/asset/ux_fixture?version=${v}`); await capture(page, name); }
  await page.getByRole('button', { name: 'Edit animation', exact: true }).click(); await page.getByLabel('Clip to edit').waitFor(); await capture(page, 'animation-editor');
  await probe('unsaved_animation_close', async () => {
    await page.getByText('Clip tools', { exact: true }).click();
    await page.getByLabel('Speed', { exact: true }).fill('0.5'); await page.getByLabel('Speed', { exact: true }).blur();
    const before = { saveEnabled: await page.getByRole('button', { name: 'Save as a new version' }).isEnabled() };
    let dialogs = 0; const listener = d => { dialogs++; d.dismiss(); }; page.on('dialog', listener);
    await page.locator('.anim-editor').getByRole('button', { name: 'Close', exact: true }).click();
    const closed = (await page.getByLabel('Clip to edit').count()) === 0;
    await page.getByRole('button', { name: 'Edit animation', exact: true }).click(); await page.getByText('Clip tools', { exact: true }).click();
    const reopenedSpeed = await page.getByLabel('Speed', { exact: true }).inputValue();
    page.off('dialog', listener);
    return { ...before, dialogs, closed, reopenedSpeed, posts: state.posts };
  });
  await go(page, '#/asset/ux_fixture?version=009_bake');
  await page.getByRole('button', { name: /^History/ }).click(); await capture(page, 'history');
  await probe('history_keyboard_focus', async () => {
    const order = [];
    for (let i = 0; i < 75; i++) { await page.keyboard.press('Tab'); order.push(await page.evaluate(() => { const el = document.activeElement, r = el.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return { tag: el.tagName, name: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 90), insideDrawer: !!el.closest('.drawer'), obscuredByDrawer: !el.closest('.drawer') && !!top?.closest('.drawer'), rect: { x: Math.round(r.x), y: Math.round(r.y) } }; })); }
    await page.getByRole('button', { name: 'Frame model', exact: true }).focus(); await page.keyboard.press('Escape');
    return { order, drawerRemainsAfterEscapeFromPreview: await page.getByRole('dialog', { name: 'History', exact: true }).count() };
  });
  await go(page, '#/asset/ux_fixture?version=009_bake'); await page.getByRole('button', { name: 'Licences', exact: true }).click(); await page.getByRole('dialog', { name: 'Licences', exact: true }).waitFor(); await page.waitForTimeout(200); await capture(page, 'licences');
  await probe('licences_layout', async () => ({ layout: await page.evaluate(() => { const ws = document.querySelector('.workspace'); return { workspaceRows: getComputedStyle(ws).gridTemplateRows, children: [...ws.children].map(el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el); return { className: el.className, height: Math.round(r.height), top: Math.round(r.top), gridRow: s.gridRow, text: el.className === 'licences' ? el.innerText : undefined }; }), licenceHitAtHeading: document.elementFromPoint(30, 175)?.closest('.licences') != null }; }) }));
  await go(page, '#/asset/ux_fixture?version=009_bake'); await page.getByRole('button', { name: /^History/ }).click(); await page.getByRole('button', { name: /^Compare Generated model.*005/ }).click(); await page.locator('.compare').waitFor(); await page.getByRole('button', { name: 'Close', exact: true }).first().click(); await capture(page, 'compare');
  await probe('preparation_copy_with_active_job', async () => {
    await go(page, '#/asset/ux_fixture?version=009_bake');
    await page.evaluate(() => { window.uxSource.emit('progress', { job_id: 'fixture_job', asset_id: 'ux_fixture', step: 'validate', p: .3, text: 'Checking mesh' }); window.uxSource.emit('job', { job_id: 'fixture_job', status: 'running' }); });
    return { panelText: await page.getByLabel('Next step', { exact: true }).innerText() };
  });
  await page.setViewportSize({ width: 1280, height: 720 });
  for (const [name, v] of [['laptop-bake', '009_bake'], ['laptop-imported', '012_import_model'], ['laptop-generate', '004_prep'], ['laptop-prepare', '005_trellis2'], ['laptop-skin', '013_rig_skin']]) { await go(page, `#/asset/ux_fixture?version=${v}`); await capture(page, name); }
  await go(page, '#/asset/ux_fixture?version=014_anim'); await page.getByRole('button', { name: 'Edit animation', exact: true }).click(); await page.getByLabel('Clip to edit').waitFor(); await capture(page, 'laptop-editor');
  await probe('failed_save_retains_editor', async () => {
    await page.getByText('Clip tools', { exact: true }).click(); await page.getByLabel('Speed', { exact: true }).fill('0.5'); await page.getByLabel('Speed', { exact: true }).blur(); state.failSave = true;
    await page.getByRole('button', { name: 'Save as a new version' }).click(); await page.getByRole('alert').filter({ hasText: 'Fixture save refused' }).waitFor();
    return { editorCount: await page.getByLabel('Clip to edit').count(), speed: await page.getByLabel('Speed', { exact: true }).inputValue(), saveEnabled: await page.getByRole('button', { name: 'Save as a new version' }).isEnabled() };
  });
  await probe('library_filter_navigation', async () => {
    await go(page, '#/library'); await page.getByLabel('Search assets').fill('Dragon'); const before = await page.locator('.cards li').count();
    await page.getByRole('navigation').getByRole('link', { name: 'Setup', exact: true }).click(); await page.getByRole('navigation').getByRole('link', { name: 'Library', exact: true }).click();
    return { before, searchOnReturn: await page.getByLabel('Search assets').inputValue(), cardsOnReturn: await page.locator('.cards li').count(), hash: await page.evaluate(() => location.hash) };
  });
  await probe('missing_feature_actions', async () => {
    state.missing = true; await go(page, '#/new'); await page.getByLabel('Description', { exact: true }).fill('Fixture lantern');
    const concepts = { warning: await page.getByText("Concept-image files weren't found.", { exact: false }).count(), enabled: await page.getByRole('button', { name: 'Generate 4 concepts', exact: true }).isEnabled() };
    await capture(page, 'missing-concepts');
    await go(page, '#/asset/ux_fixture?version=004_prep'); const generate = { warning: await page.getByText("generator's files weren't found.", { exact: false }).count(), enabled: await page.getByRole('button', { name: 'Generate 3D', exact: true }).isEnabled() };
    await capture(page, 'missing-generator'); state.missing = false; return { concepts, generate };
  });
  await probe('contrast_and_structure', async () => {
    await go(page, '#/new');
    return await page.evaluate(() => {
      const rgb = c => c.match(/[\d.]+/g).slice(0, 3).map(Number);
      const lum = c => rgb(c).map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4).reduce((t, x, i) => t + x * [.2126, .7152, .0722][i], 0);
      const ratio = (a, b) => +((Math.max(lum(a), lum(b)) + .05) / (Math.min(lum(a), lum(b)) + .05)).toFixed(2);
      const control = document.querySelector('textarea'); const c = getComputedStyle(control); const p = getComputedStyle(document.querySelector('.page:not([hidden])'));
      const root = getComputedStyle(document.documentElement); const color = token => { const el = document.createElement('span'); el.style.color = root.getPropertyValue(token); document.body.append(el); const result = getComputedStyle(el).color; el.remove(); return result; };
      return { textVsPage: ratio(color('--text'), color('--page')), secondaryVsPanel: ratio(color('--text-2'), color('--panel')), inputBorderVsPage: ratio(c.borderTopColor, p.backgroundColor === 'rgba(0, 0, 0, 0)' ? color('--page') : p.backgroundColor), inputBorderVsFill: ratio(c.borderTopColor, c.backgroundColor), placeholderColor: getComputedStyle(control, '::placeholder').color, skipLinks: document.querySelectorAll('a[href="#main-content"]').length };
    });
  });
  const compact = await setup({ width: 390, height: 844 });
  for (const [name, hash] of [['compact-library', '#/library'], ['compact-new', '#/new'], ['compact-import', '#/import'], ['compact-workspace', '#/asset/ux_fixture?version=012_import_model'], ['compact-concepts', '#/asset/ux_fixture?version=003_concepts']]) { await go(compact.page, hash); await capture(compact.page, name, true); }
  await compact.context.close();
  const zoom = await setup({ width: 640, height: 360 }); await go(zoom.page, '#/asset/ux_fixture?version=014_anim'); await zoom.page.getByRole('button', { name: 'Edit animation', exact: true }).click(); await zoom.page.getByLabel('Clip to edit').waitFor(); await capture(zoom.page, 'zoom-equivalent-editor', true); await zoom.context.close();
  state.empty = true; await page.setViewportSize({ width: 1440, height: 900 }); await go(page, '#/library'); await capture(page, 'empty-library');
  await context.close();
} finally { await browser?.close(); await server?.close(); save(); }
console.log(JSON.stringify({ captures: observations.captures.length, probes: observations.probes.length, probeErrors: observations.probes.filter(p => p.probeError).length, pageErrors: observations.errors }));
