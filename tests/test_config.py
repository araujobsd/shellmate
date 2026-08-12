from shellmate.config import Config, load_config


def test_missing_file_yields_defaults(tmp_path):
    cfg = load_config(tmp_path / "absent.toml")
    assert cfg == Config()
    assert cfg.character == ""  # empty defers to the sprite registry default
    assert cfg.poll_seconds == 2.0
    assert cfg.notify is False  # Claude sessions: interactive use, notifications off by default


def test_values_are_read_from_file(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('character = "owl"\npoll_seconds = 5.0\nnotify = false\n')
    cfg = load_config(p)
    assert cfg.character == "owl"
    assert cfg.poll_seconds == 5.0
    assert cfg.notify is False
    assert cfg.frame_seconds == 0.6  # untouched key keeps its default


def test_malformed_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("this is not valid toml {{{")
    assert load_config(p) == Config()


def test_unknown_keys_are_ignored(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('character = "blob"\nnonsense_key = 42\n')
    cfg = load_config(p)
    assert cfg.character == "blob"


def test_wrong_type_falls_back_for_that_key_only(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('character = "owl"\npoll_seconds = "fast"\n')
    cfg = load_config(p)
    assert cfg.character == "owl"
    assert cfg.poll_seconds == 2.0


def test_unknown_character_is_passed_through_untouched(tmp_path):
    # config does not validate the name; characters.frames_for() owns the fallback
    p = tmp_path / "config.toml"
    p.write_text('character = "tyrannosaurus"\n')
    assert load_config(p).character == "tyrannosaurus"


def test_show_phrase_defaults_to_true():
    cfg = Config()
    assert cfg.show_phrase is True


def test_show_phrase_can_be_disabled(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("show_phrase = false\n")
    cfg = load_config(p)
    assert cfg.show_phrase is False
