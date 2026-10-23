"""Effigy GLB/UV projection for shared four-channel diffusion textures."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.transforms.functional import gaussian_blur

from server.paint_contracts import CameraBinding
from steps._bake import rasterize_uv
from steps._paint_set import Surface
from steps._views import ortho


@dataclass(frozen=True)
class ProjectionMap:
    uv_grid: torch.Tensor
    silhouette: torch.Tensor
    view_grid: torch.Tensor
    weights: torch.Tensor


class LatentRenderer:
    def __init__(self, surface: Surface, cameras: tuple[CameraBinding, ...], device: torch.device,
                 dtype: torch.dtype, selected: np.ndarray):
        self.texture_size = surface.size // 8
        self.cameras = cameras
        self.maps: list[ProjectionMap] = []
        self.normals: list[torch.Tensor] = []
        atlas_ids, bary = rasterize_uv(surface.uv, surface.faces, self.texture_size)
        owner = atlas_ids.numpy()
        covered = owner >= 0
        ids = owner[covered]
        points = (surface.vertices[np.asarray(surface.mesh.faces)[ids]] * bary.numpy()[covered, :, None]).sum(1)
        normals = np.asarray(surface.mesh.face_normals)[ids]
        self.covered = torch.tensor(covered, device=device)
        self.permission = (F.avg_pool2d(torch.tensor(selected.astype(np.float32), device=device)[None, None], 8) >= 0.999).to(dtype)
        for binding in cameras:
            view = {"yaw": binding.yaw, "pitch": binding.pitch, "center": binding.center, "extent": binding.extent}
            camera = ortho(**view)
            face_image, face_bary = surface.raster(view, 64)
            seen = face_image >= 0
            image_uv = np.zeros((64, 64, 2), dtype=np.float32)
            image_uv[seen] = (surface.uv.numpy()[np.asarray(surface.mesh.faces)[face_image[seen]]] * face_bary[seen, :, None]).sum(1)
            pix, _ = camera["project"](points)
            xy = np.floor(pix * 64).astype(int).clip(0, 63)
            facing = (normals * camera["towards"](points)).sum(1)
            visible = ((pix >= 0) & (pix < 1)).all(1) & (face_image[xy[:, 1], xy[:, 0]] == ids) & (facing > 0.25)
            weights = torch.tensor((visible * facing.clip(0, 1) ** 2).astype(np.float32), device=device, dtype=dtype)
            self.maps.append(ProjectionMap(
                torch.tensor(image_uv * 2 - 1, device=device, dtype=dtype)[None],
                torch.tensor(seen, device=device)[None, None],
                torch.tensor(pix * 2 - 1, device=device, dtype=dtype).reshape(1, 1, -1, 2), weights))
            high_ids, _ = surface.raster(view, 512)
            drawn = high_ids >= 0
            y, p = math.radians(binding.yaw), math.radians(-binding.pitch)
            ry = np.array([[math.cos(y), 0, -math.sin(y)], [0, 1, 0], [math.sin(y), 0, math.cos(y)]])
            rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
            image = np.zeros((512, 512, 3), dtype=np.float32)
            image[..., 2] = 1
            image[drawn] = np.asarray(surface.mesh.face_normals)[high_ids[drawn]] @ (rx @ ry).T
            # Upstream get_conditioning_images supplies signed camera-space normals.
            normal = torch.tensor(image, device=device, dtype=dtype).permute(2, 0, 1)[None]
            self.normals.append(gaussian_blur(normal, [5, 5], [2.0, 2.0])[0])

    def bake(self, views: torch.Tensor, fallback: torch.Tensor) -> torch.Tensor:
        colours = torch.zeros((views.shape[1], int(self.covered.sum())), device=views.device, dtype=views.dtype)
        weights = torch.zeros(colours.shape[1], device=views.device, dtype=views.dtype)
        for index, mapping in enumerate(self.maps):
            sampled = F.grid_sample(views[index:index + 1], mapping.view_grid, align_corners=False, padding_mode="border")[0, :, 0]
            colours += sampled * mapping.weights[None]
            weights += mapping.weights
        result = fallback.clone()
        previous = result[0, :, self.covered]
        result[0, :, self.covered] = torch.where(weights[None] > 0, colours / weights.clamp(min=1e-6)[None], previous)
        return result

    def render(self, texture: torch.Tensor, background: torch.Tensor) -> torch.Tensor:
        rows: list[torch.Tensor] = []
        for index, mapping in enumerate(self.maps):
            projected = F.grid_sample(texture, mapping.uv_grid, align_corners=False, padding_mode="border")
            rows.append(torch.where(mapping.silhouette, projected, background[index:index + 1]))
        return torch.cat(rows)

    def neighbours(self) -> list[list[int]]:
        directions = []
        for camera in self.cameras:
            view = ortho(camera.yaw, camera.pitch, camera.center, camera.extent)
            directions.append(view["towards"](np.zeros((1, 3)))[0])
        return [[i, *sorted((j for j in range(len(directions)) if j != i),
                            key=lambda j: (-float(directions[i] @ directions[j]), self.cameras[j].camera_id))[:2]]
                for i in range(len(directions))]
