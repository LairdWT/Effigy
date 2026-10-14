# Your laptop session: set up, try it, measure it

Everything so far was built and tested on CPUs in the cloud. Your laptop is the first real GPU it runs
on, so this session has two goals: **does it work**, and **how fast / how much memory**. Tick the boxes as
you go and note anything odd. At the end you send me a few files and notes (Part 6), and I fix what
broke and put the numbers into the docs.

**Before you start**: laptop plugged in, Windows power mode "Best performance", games and video apps
closed, browser with few tabs. Allow ~4 hours, most of it waiting (downloads, benchmark).

If something fails: copy the error text (the job list at the bottom of the app shows it, the black
`run.bat` window has more), note what you clicked, and carry on with the next part if you can.

### Waiting for DINOv3 approval?

DINOv3 is only needed by the **3D generators (Fast, Faithful) and retexture**. Everything else works
without it, so do this now and the rest when the approval email arrives:

| Now, without DINOv3 | After approval |
|---|---|
| Part 1 completely; on the Models page install **fast, concepts, faithful** anyway (they download everything except DINOv3 and end with `gated`, that's expected) | Log in (`hf auth login`, SETUP step 6), click **Install fast** again: only DINOv3 is fetched |
| Part 2 step 1 (text → 4 concepts) and picking with "cut out only" | Part 2 steps 2–7 (3D generation, game-ready chain on it, retexture, Faithful) |
| Part 4 step 1: make the 10 test images (`--make-golden`) | Part 4 steps 2–4 (the Fast/Faithful benchmark) |
| **Your own GLB** instead of a generated one: Create → choose any `.glb` you have (no texture needed) → **Create from image**; then on that version run `clean` → `remesh {"faces": 10000}` → `uv` → `validate` → `export` (`godot`, `unreal`). That tests the game-ready chain and lets you do **Part 5** (engine imports) | `bake` and `retexture` on generated assets |
| Part 3 steps 1–3 (Blender open/pull) with that GLB asset, and step 5 (Ask Claude) | Part 3 step 4 (retexture the pulled mesh) |

---

## Part 1: Set up (follow docs/SETUP.md steps 1–6)

- [ ] **Step 1** driver: note the driver version from `nvidia-smi`: ________
- [ ] **Step 2–4** zip + first start: **time it** from double-clicking `run.bat` until the page shows
      "GPU: idle": ________ min. (Your home-internet number for the install table.)
- [ ] **Step 5** GPU check: copy the three lines it prints (or the error).
- [ ] **Step 6** Hugging Face + Models page: install **fast**, then **concepts**, then **faithful**.
      Note anything that fails (especially `gated`).

## Part 2: One asset by hand (~30–60 min)

This tries every step once. Follow SETUP.md step 7.

1. [ ] **Text → 4 concepts**: Create → *"wooden storage crate with iron corner brackets"*, `prop`,
       **Make 4 concepts**. Did 4 images appear? How long (roughly)? ________
2. [ ] **Pick → Fast 3D**: "pick = cut out + generate: fast" → **pick** on the best image. Note how long
       until the model shows: ________ (the first run includes loading the models and a one-time GPU
       tuning; a second generation shows the normal time).
3. [ ] **Look at it** in the viewer (rotate; switch the view modes). Does it match the picture?
4. [ ] **Game-ready chain** with "Run a step", each on the version the previous one created:
       `clean {}` → `remesh {"faces": 10000}` → `uv {}` → `bake {"texture_size": 2048}` →
       `validate {"max_triangles": 10000}`. Each one ✓ or ✗: ______________________
5. [ ] **Export** from the `bake` version: `export {"profile": "godot"}` and `export {"profile": "unreal"}`.
       Files appear under `C:\Effigy\library\<asset>\<NNN>_export\`?
6. [ ] **Retexture**: on the `bake` version run step `trellis2`, preset **retexture**. New textures, same
       shape? How long? ________
7. [ ] **Faithful**: click the `…_concepts` version again, choose "pick = cut out + generate: **faithful**",
       pick the same image. Works? How long? Closer to the picture than Fast? ________

## Part 3: Blender round trip (optional, ~15 min)

Needs the Blender MCP Pro add-on (SETUP.md step 8).

1. [ ] Click the `bake` version → **Open in Blender**. The model appears in Blender?
2. [ ] Change something visible (e.g. scale one part, or move a few vertices). Don't touch the UVs.
3. [ ] **Pull from Blender** → a new `…_blender` version appears?
4. [ ] On that version run `trellis2` with the **retexture** preset → it gets new textures that fit the
       edited shape? (This is the M12 check: the mesh and its UVs must come back unchanged.)
5. [ ] (Optional, Claude subscription) **Ask Claude…** with a preset on a version → it works in Blender,
       then **accept** or **revert** works?

## Part 4: The benchmark (~1–3 h, unattended)

This runs the same chain on 10 standard images, once with Fast and once with Faithful, and writes all
timings and memory peaks into spreadsheet files. Keep the app (`run.bat`) running. In a PowerShell
window in the app folder (SETUP.md step 5 shows how):

1. [ ] Make the 10 test images (once):

   ```powershell
   .\.venv\Scripts\python.exe -m tools.bench --make-golden
   ```

   They land in `tests\fixtures\golden\` (crate, barrel, lantern, …). Open them: if one is unusable
   (cut off, several objects, …), tell me which.
2. [ ] Fast:

   ```powershell
   .\.venv\Scripts\python.exe -m tools.bench --weights fast --out docs\bench\phase0_fast.csv
   ```

   It prints a summary at the end ("10/10 succeeded …"). Copy it.
3. [ ] Faithful:

   ```powershell
   .\.venv\Scripts\python.exe -m tools.bench --weights faithful --out docs\bench\phase0_faithful.csv
   ```

   Copy its summary too.
4. [ ] **Fast vs Faithful**: the benchmark made 20 assets named `bench crate`, `bench barrel`, …
       (two of each). For each of the 10 objects, open both in the app and note which one looks more
       like its image: Fast ____ / Faithful ____ / tie ____.

Leave the laptop alone while it runs (no games); sleep mode must be off for that time.

## Part 5: Engine imports (Godot and Unreal; Unity only if you like)

Use the exports from Part 2 step 5. Follow the checklist in `docs/bench/m13.md` (Godot and Unreal
sections): scale (1 m = 1 unit), upright, the 4 LODs in Unreal, collision recognised, textures
present. Tick what works, note what doesn't.

## Part 6: What to send me

Attach or paste in our chat:

1. Your notes from Parts 1–5 (the ticks, times, ✓/✗, error texts).
2. The files `C:\Effigy\docs\bench\phase0_fast.csv` and `phase0_faithful.csv`.
3. The two benchmark summaries and the Fast-vs-Faithful tally.
4. Screenshots of anything that looks wrong (a model, a texture, an engine import).

That's everything I need to fix problems, fill in the measured numbers (install time, generation
times, memory), pick the default generator, and close Phase 0 and Phase 1.
