---
id: c73be29e-123c-4de7-aa3f-faac9b354535
slug: adr:isolate-the-syncmvd-adaptation-and-pinned-dependencies
title: Isolate the SyncMVD adaptation and pinned dependencies
status: superseded
supersedes: []
supersededBy: adr:use-the-approved-ungated-sd1-5-mirror-for-syncmvd
deciders: ["user"]
proposedAt: 2026-10-21
decidedAt: 2026-10-21
tags: []
---

## Context

The owner approved a four-method full-view painting comparison on 2026-10-21. Existing native FIBO, Genesis and MOSS engines edit images without sharing a texture state during denoising. SyncMVD provides published synchronized DDPM equations and samplewise attention, but its original PyTorch3D renderer does not match Effigy's GLB, immutable UV, permission-mask and Windows runtime contract.

## Decision

Use SyncMVD source pinned to faa95621d220d7327847a994cd380608c04af5ab as the attributed algorithm reference. Adapt scheduler and attention logic behind Effigy-owned renderer and mask interfaces. Do not install PyTorch3D, change topology or unwrap UVs.

Create a dedicated Python 3.12 environment with Torch 2.8/CUDA 12.8, Diffusers 0.40.0 and Transformers 5.18.0, plus their separately frozen dependencies. Reuse these already selected library versions instead of upgrading existing environments. Provision stable-diffusion-v1-5 at 3ae886b8ac1eb511e51629a7551839d68ea5398a and control_v11p_sd15_normalbae at cb7296e6587a219068e9d65864e38729cd862aa8 using the required FP16 safetensors and supporting configurations. Models live in Effigy-owned NAS storage; environment and source cache remain on D:.

Explicit provisioning may access public package/model repositories. Generation remains offline and resolves pinned local paths. Source implementations stay canonical in Effigy; activate only the trial lane on port 8380. Borrowed MOSS and other model assets remain read-only.

## Consequences

Existing native and ML runtimes remain independent. Separate dependency resolution and local snapshot bindings are maintainable and reproducible. This adds an isolated environment and new model storage. The masked renderer adaptation requires technical and visual qualification; upstream success is not evidence of Effigy output quality. Runtime must preserve protected context at the current noise level and exact RGB/alpha after decoding.

## Alternatives

- Reimplement all diffusion, transformer and weight-loading infrastructure: rejected because it duplicates mature existing libraries and greatly expands correctness risk beyond the bounded renderer adaptation.
- Install upstream SyncMVD unchanged with PyTorch3D: rejected because it conflicts with the approved environment and geometry contract.
- Use six-view MV-Adapter: rejected by the owner because its fixed cameras miss required selected texels.
- Continue independent paired edits only: retained historically, but insufficient for the newly approved shared-context comparison.
