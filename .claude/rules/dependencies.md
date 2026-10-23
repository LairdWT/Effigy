---
paths:
  - "pyproject.toml"
  - "**/pyproject.toml"
  - "requirements*.txt"
  - "**/requirements*.txt"
  - "package.json"
  - "**/package.json"
---

A new third-party dependency needs explicit user approval AND an accepted
ADR recording why the capability cannot reasonably be built in-repo.
Prefer the standard library or a hand-rolled implementation. Put the
build-vs-buy reasoning in the ADR, never in a code comment. The guard
hook blocks a manifest edit that adds a dependency name not already
present; do not add one unilaterally.
