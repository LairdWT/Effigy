import sys

import pytest

from engine.trellis2.patches import install_nvdiffrast_decoy


def test_decoy_imports_but_refuses_use():
    install_nvdiffrast_decoy()
    import nvdiffrast.torch as dr  # what o_voxel/postprocess.py does at import time

    with pytest.raises(ImportError, match="non-commercial"):
        dr.RasterizeCudaContext()
    for name in ("nvdiffrast", "nvdiffrast.torch"):
        del sys.modules[name]
