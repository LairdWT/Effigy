# Backend code review — 2026-10-05

## Scope

Reviewed the backend API, asset/version storage, job lifecycle, cancellation, and Blender integration at commit `149d791`. This follows the calculation and inference review in [CODE_REVIEW_2026-10-05.md](CODE_REVIEW_2026-10-05.md).

Primary files reviewed: `server/app.py`, `server/library.py`, `server/jobs.py`, `server/claude_runner.py`, `server/blender_client.py`, `server/models.py`, `server/thumbs.py`, `mcp/lt2_server.py`, and `steps/_blender.py`, with the related tests and the contracts in `docs/IMPLEMENTATION.md`.

This was a review only. No application code was changed. Reproductions used temporary libraries and mocked Blender commands; no live Blender scene was changed.

## Findings

### 1. HIGH — Revert removes live objects before validating the restore target

**Locations:** `server/blender_client.py:227–230`, `server/app.py:73–81`, and the accept/revert lifecycle in `server/claude_runner.py`.

`blender_client.revert()` executes `REMOVE` before `open_version()` resolves and validates the snapshot to restore. Meanwhile, the API's idle check only blocks queued/running jobs. A completed Claude run awaiting review still needs its snapshot, but that snapshot can be deleted through the version API.

**Reproduction:** In a temporary library, create an upload and a Blender snapshot, then register a completed Claude run whose review remains open. Deleting the snapshot returns HTTP 200. Reverting the run then returns HTTP 404, but the mocked Blender command log already contains `REMOVE`.

**Impact:** Revert can remove the asset's objects from the live Blender scene and then fail to restore them. The snapshot may remain recoverable from trash, but the operation has already changed the scene before discovering that its prerequisite is unavailable.

**Recommendation:** Resolve and validate the restore target before issuing destructive scene commands. Protect snapshots referenced by runs awaiting accept/revert, and make the restore operation preserve the current scene if loading the snapshot fails.

### 2. HIGH — Version allocation fails at 1000 and can loop indefinitely

**Locations:** `server/library.py:13`, `server/library.py:131–143`, `server/library.py:158`.

The version regex accepts exactly three digits, but allocation formats `max + 10` with a minimum width of three digits. After `990_*`, it creates `1000_*`, which the same regex does not recognize. Metadata writing then fails when it indexes the failed regex match. A subsequent allocation for the same step repeatedly attempts the existing `1000_*` directory because that directory is excluded from the maximum-version scan.

**Reproduction:** Start with `990_upload` in a temporary asset. `new_version(..., "upload")` creates `1000_upload`, for which the version regex returns no match. `write_meta()` raises `TypeError: 'NoneType' object is not subscriptable`. The next allocation candidate remains the already-existing `1000_upload`.

The infinite loop itself was not executed: the reproduction established the repeated candidate and existing-directory condition directly.

**Impact:** The 100th normal allocation becomes unusable. A later attempt for the same step can occupy a worker indefinitely; inside the global GPU lock, this also prevents other queued work from proceeding.

**Recommendation:** Add an explicit exhaustion check under the current documented `NNN_step` contract. If longer version numbers are desired, migrate every reader, validator, UI parser, and Blender naming assumption together. Do not silently create directories that the library cannot read.

### 3. MEDIUM — Cancellation leaves subprocess descendants running

**Locations:** `server/jobs.py:282–294`, `steps/_blender.py:36`.

Cancellation marks a job cancelled and terminates its tracked Python process. Blender-based steps launch another process through `subprocess.run()`. The cancellation path does not terminate or wait for that descendant process tree.

**Reproduction:** A harmless Python parent launched a child that waited briefly and wrote a marker file. Cancelling through the actual job cancellation function terminated the parent, but the child subsequently wrote its marker. Observed: job status `cancelled`, parent exited, child completed after cancellation. No Blender process was launched for this probe.

**Impact:** Cancelled work can continue consuming resources and writing files. Once the parent exits, the scheduler can release the GPU lock while a descendant still runs, allowing overlapping work that the lock was intended to prevent.

**Recommendation:** Own and terminate the complete subprocess tree, using a suitable Windows process-management mechanism such as a Job Object. Wait for descendants to exit before releasing resources or treating cancellation as complete.

### 4. MEDIUM — Concurrent Blender pulls can save the wrong exported scene

**Location:** `server/blender_client.py:204–212`.

Every pull uses the same asset-level `inbox` directory. Each request deletes and recreates that directory, asks Blender to export into it, and then moves its contents into a new version. There is no lock or request-specific staging directory around this sequence.

**Reproduction:** Two controlled, mocked pull requests for the same temporary asset were interleaved. Request A exported A and paused before returning. Request B replaced the shared staging directory with export B. A then saved B into `020_blender`; B subsequently failed with `FileNotFoundError` after A consumed the files.

Observed result:

```text
A: version=020_blender, mesh=B
B: FileNotFoundError
```

**Impact:** The recorded version can contain another request's export, and a concurrent request can leave an incomplete version. A single UI's busy guard does not serialize calls from multiple clients or MCP/API callers.

**Recommendation:** Serialize the pull operation per asset or use unique staging directories per request. Also ensure that each scene export is captured consistently if live Blender operations can overlap.

### 5. MEDIUM — Metadata finalization failures leave jobs permanently running

**Location:** `server/jobs.py:331–366`, especially output validation at line 351 and metadata writing at line 355.

The exception handler around step execution ends before output validation and `library.write_meta()`. If either finalization operation raises, the exception escapes the worker without assigning a terminal job status.

**Reproduction:** Run the real `_run()` function with a successful mocked step and inject an `OSError` from metadata writing. The exception escapes; the job remains `running` with no recorded error after its worker has stopped.

**Impact:** UI and MCP callers can keep waiting indefinitely. Asset operations guarded by the idle check remain blocked even though there is no active computation. Disk/write failures therefore become persistent false-running state rather than a recoverable failed job.

**Recommendation:** Include output validation, metadata writing, and finalization in the error boundary. Ensure every exit path records a terminal state and useful error, with cleanup handled separately so cleanup errors do not hide the original failure.

## Verification

Existing targeted tests were run locally:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_library.py tests/test_claude_runner.py tests/test_blender_client.py tests/test_lt2_mcp.py tests/test_thumbs.py -q
```

Result: **27 passed, 1 skipped in 16.10 seconds**. The skipped test uses a shell-based fake Claude executable that is incompatible with Windows.

Additional isolated probes established each finding as described above. Blender interactions were mocked; these results do not constitute a live Blender integration test. No CI run was triggered and no application source files were modified.

## Recommended order

1. Prevent destructive revert before restore validation and protect pending-review snapshots.
2. Stop version allocation cleanly at the documented format limit.
3. Guarantee terminal job states when finalization fails.
4. Terminate subprocess descendants during cancellation.
5. Isolate or serialize Blender pull staging.

## Outcome (2026-10-05, same day)

All five confirmed by reading the code; implemented on branch `review-fixes` with a test each.

1. **Revert**: `blender_client.revert` resolves the version and its mesh (`_model`, shared with
   `open_version`) before `REMOVE`; a missing snapshot is a 404 with nothing sent to Blender. The delete
   guard (`app._idle`) also refuses to delete a version that is the snapshot of a finished Claude run
   still waiting for accept / revert (409).
2. **Version numbers**: `library.new_version` stops at 990 with a clear 409 ("used up its version
   numbers") instead of creating `1000_*`. Widening to four digits is a contract change (§3.2) that
   touches the library regex, the Blender collection names (`v{version[:3]}` in three places), the
   texture step's version lookup, the UI's `.slice(0, 3)` labels and its string sort of versions: proposed
   to the owner, not done. The dwarf asset stands at 620: 37 versions left.
3. **Cancellation**: `jobs._kill_tree` takes the step's children too (`taskkill /T` on Windows, the
   step's own process group on POSIX, started with `start_new_session`).
4. **Concurrent pulls**: Blender exports straight into the new version folder (unique per request); no
   shared `inbox`. A failed export removes the folder.
5. **Finalization**: output validation and `write_meta` are inside the job's error boundary; a failure
   there ends the job as `failed` with the message, and nothing half-written stays.
