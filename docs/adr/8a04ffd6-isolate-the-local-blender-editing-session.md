---
id: 8a04ffd6-f11a-478e-b811-809803fa74d1
slug: adr:isolate-the-local-blender-editing-session
title: Isolate the local Blender editing session
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-20
decidedAt: 2026-10-20
tags: []
---

## Context
Effigy's upstream live bridge tries ports 9877 and 9876. This workstation already has an unrelated Blender scene on 9877. Sending Effigy editing snippets there would violate the owner's requirement to preserve other work. The configured local-only MCP for Blender fork is already installed and implements the free add-on's socket protocol.

## Decision
Set an explicit local binding to loopback port 8371 and do not fall back to other Blender ports when that binding exists. Resolve both the Blender executable and installed local add-on through 3DGen tools.config.json. Launch a separate factory-startup, offline Blender session with Effigy-owned profile and scratch directories. Load the existing add-on read-only in that session; no installation or preference change reaches the owner's normal Blender profile. The standard Effigy Open, Pull, and Close API operations use this isolated session.

## Consequences
Interactive edits and round-trip acceptance use a separate scene while the owner's current scene and MCP configuration remain intact. Python network controls and Blender offline mode apply to the isolated process. The bridge is local application transport and is not registered with a hosted assistant. The isolated session remains open for user editing after an application restart. Runtime acceptance must exercise Open and Pull and observe its connections.

## Alternatives
- Reuse the listener on 9877: rejected because the owner's unrelated scene must remain untouched.
- Download another Blender or add-on: unnecessary; existing configured tools provide the required protocol.
- Accept exports alone as interactive round-trip proof: insufficient for Open and Pull compatibility.
