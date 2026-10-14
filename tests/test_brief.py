"""steps/brief.py: the prompt and its category template."""


def test_the_brief_keeps_the_prompts_own_view(tmp_path):
    """The owner's agent (2026-10-11): "front elevation, seen straight on" got "three-quarter view" appended; a
    prompt that names its view keeps it, one that does not gets the template's."""
    import yaml

    from steps import brief

    brief.run(
        "run",
        None,
        tmp_path,
        {"prompt": "a timber fence bay, front elevation, seen straight on", "category": "prop"},
    )
    full = yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
    assert "three-quarter" not in full and "product photograph" in full
    brief.run("run", None, tmp_path, {"prompt": "a timber fence bay", "category": "prop"})
    full = yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
    # a level camera (the owner's agent, 2026-10-13: a concept shot from above makes a model that leans)
    assert "three-quarter view" in full and "the camera level at mid height" in full
    for own in (
        "a well, seen from above",
        "a well, the camera low",
    ):  # its own camera: the template's goes
        brief.run("run", None, tmp_path, {"prompt": own, "category": "prop"})
        full = yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
        assert "camera level" not in full and "three-quarter" not in full, own
    for words in (
        "an overview map",
        "a security camera",
        "a sign above a door",
    ):  # objects, not views
        brief.run("run", None, tmp_path, {"prompt": words, "category": "prop"})
        full = yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
        assert "the camera level at mid height" in full, words


def test_the_2d_categories_frame_a_picture(tmp_path):
    """M50: wallpaper, background, portrait, icon and item frame a picture for concepts op image; no 3D framing."""
    import yaml

    from steps import brief

    for category in ("wallpaper", "background", "portrait", "icon", "item"):
        brief.run("run", None, tmp_path, {"prompt": "a neon street", "category": category})
        full = yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
        assert (
            full.startswith("a neon street, ")
            and "A-pose" not in full
            and "product photograph" not in full
        )
    brief.run(
        "run", None, tmp_path, {"prompt": "a neon street", "category": "picture"}
    )  # nothing added
    assert (
        yaml.safe_load((tmp_path / "brief.yaml").read_text(encoding="utf-8"))["prompt_full"]
        == "a neon street"
    )
