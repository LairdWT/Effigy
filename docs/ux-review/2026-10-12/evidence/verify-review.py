"""Check review completeness, evidence links and unchanged tracked source."""
import json
import re
import subprocess
from pathlib import Path

review = Path(__file__).resolve().parents[1]
root = review.parents[2]
required = ["README.md", "PLAN.md", "STATE.md", "WORKFLOWS.md", "FINDINGS.md", "IMPROVEMENTS.md", "evidence/VALIDATION.md"]
for name in required:
    assert (review / name).is_file(), name

links = 0
for document in review.rglob("*.md"):
    content = document.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if target.startswith(("https://", "http://", "#")):
            continue
        target = target.split("#", 1)[0]
        assert (document.parent / target).resolve().exists(), f"{document.name}: {target}"
        links += 1

findings = (review / "FINDINGS.md").read_text(encoding="utf-8")
ids = re.findall(r"^## (UX-\d+) ", findings, re.M)
assert ids == [f"UX-{i:02}" for i in range(1, 16)], ids
workflows = (review / "WORKFLOWS.md").read_text(encoding="utf-8")
assert len(re.findall(r"^\| W\d+ \|", workflows, re.M)) == 14

data = json.loads((review / "evidence/observations.json").read_text(encoding="utf-8"))
assert len(data["captures"]) == 34
assert len(data["probes"]) == 8
assert not data["errors"], data["errors"]
assert not [p for p in data["probes"] if p.get("probeError")]
for capture in data["captures"]:
    assert (review / "evidence" / capture["path"]).is_file(), capture["path"]

changed = subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip()
assert not changed, f"Tracked source changed: {changed}"
assert "| Verify review artifacts and handoff | Complete |" in (review / "STATE.md").read_text(encoding="utf-8")
print(f"PASS: 7 required Markdown files; {len(ids)} findings; 14 workflows; {links} local links; 34 screenshots; 8 probes without errors; tracked source unchanged.")
