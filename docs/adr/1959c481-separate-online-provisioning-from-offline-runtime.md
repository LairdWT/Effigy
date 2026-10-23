---
id: 1959c481-aaaf-4e6b-84d0-71964501c894
slug: adr:separate-online-provisioning-from-offline-runtime
title: Separate online provisioning from offline runtime
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
The owner selected separate online provisioning and offline runtime on 2026-10-19. Upstream startup synchronizes dependencies and Setup queries Hugging Face.

## Decision
Separate provisioning from runtime. Runtime binds loopback, uses local model paths, disables telemetry and online setup/account actions, and never downloads automatically. Propagate offline controls to every worker. Public downloads and their required integrity checks belong only to explicit provisioning. Observe runtime connections without changing Windows firewall rules or registering hosted MCP clients.

## Consequences
Missing dependencies produce local errors. Application controls and observed samples do not prove OS containment. This records approved behavior to implement, not a claim that runtime is ready.

## Alternatives
- Retain the combined upstream launcher: rejected because ordinary startup can access package servers.
- Add OS outbound blocking: rejected because the owner selected application controls and observation.
