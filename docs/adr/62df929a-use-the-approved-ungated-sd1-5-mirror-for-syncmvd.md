---
id: 62df929a-3918-46fd-b80f-2bb1d51b50be
slug: adr:use-the-approved-ungated-sd1-5-mirror-for-syncmvd
title: Use the approved ungated SD1.5 mirror for SyncMVD
status: accepted
supersedes: [adr:isolate-the-syncmvd-adaptation-and-pinned-dependencies]
supersededBy: null
deciders: ["user"]
proposedAt: 2026-10-21
decidedAt: 2026-10-21
tags: []
---

## Context

The owner approved the isolated SyncMVD comparison, then approved the ungated SD1.5 mirror on 2026-10-21 after the initially pinned Benjamin-Paine repository returned HTTP401 and no local Hugging Face token was configured. Inspection of the requested NAS model folders found FIBO, Krea, MOSS, Flux, Qwen and video architectures, but no SD1.5 checkpoint compatible with the selected normal ControlNet. These existing models remain the whole-sheet comparison methods.

## Decision

Use stable-diffusion-v1-5/stable-diffusion-v1-5 at revision 451f4fe16113bff5a5d2269ed5ad43b0592e9a14 for the required FP16 UNet, text encoder, VAE, tokenizer and scheduler components. The public model card identifies this as an SD1.5 mirror; its UNet configuration has four input/output channels and 768-dimensional text conditioning. No numerical parity with the previously proposed distribution is claimed.

Retain normal ControlNet lllyasviel/control_v11p_sd15_normalbae at cb7296e6587a219068e9d65864e38729cd862aa8 and SyncMVD source faa95621d220d7327847a994cd380608c04af5ab with MIT attribution. Retain the separate Python3.12/Torch2.8 CUDA12.8 environment, Diffusers0.40.0, Transformers5.18.0 and frozen dependency lock. Adapt the renderer in Effigy; do not install PyTorch3D or change mesh UVs/topology.

Provisioning remains explicitly online and writes only Effigy-owned NAS storage and D: environment/scratch. Runtime remains offline. Activation stays on8380; primary8370 and borrowed models are preserved. This decision supersedes the earlier repository selection while carrying its environment and build-versus-buy constraints forward.

## Consequences

No local authentication step is needed for this public mirror. The implementation still needs runtime and visual qualification and is not a switch of the user's active FIBO/Genesis/MOSS painting session to Stable Diffusion. Existing partial provisioning remains untouched; new snapshot bindings record the selected repository and revision.

## Alternatives

- Continue with the gated Benjamin-Paine repository: owner selected the ungated mirror instead.
- Substitute installed modern Turbo architectures directly into SyncMVD: rejected for this adaptation because their denoisers, latent/text interfaces and conditioning do not match the SD1.5 normal ControlNet.
- Replace diffusion libraries in-repo: rejected because it duplicates mature model/scheduler/weight-loading infrastructure beyond the approved renderer adaptation.
