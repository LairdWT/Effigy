"""concepts: the candidates' prompt suffixes per category (a prop has no "full body")."""

import pytest

pytest.importorskip("torch")
from steps.concepts import VARIANTS, variants


def test_a_prop_is_framed_as_an_object_not_a_body():
    assert variants("character") == VARIANTS
    prop = variants("prop")
    assert prop[1] == ", the whole object in frame" and prop[0] == "" and prop[2:] == VARIANTS[2:]
    assert not any("body" in s or "figure" in s for s in prop)
