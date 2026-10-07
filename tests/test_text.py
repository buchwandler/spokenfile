from spokenfile import prepare_file


def test_text_preserves_line_endings_and_rewrites_visible_text(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "notes.txt"
    source.write_bytes(b"  Dr. Smith has 2 kg.\r\ncode 24\r\n")
    output = tmp_path / "notes.spoken.txt"
    result = prepare_file(source, language="en", output=output, engine=FakeEngine())
    assert output.read_bytes() == b"  Doctor Smith has two kg.\r\ncode twenty four\r\n"
    assert result.changed
    assert len(result.changes) == 3


def test_text_preserves_wide_horizontal_whitespace(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "spacing.txt"
    source.write_text("Dr.  Smith has 2 kg.\n", encoding="utf-8")
    output = tmp_path / "spacing.spoken.txt"
    prepare_file(source, language="en", output=output, engine=FakeEngine())
    assert output.read_text(encoding="utf-8") == "Doctor  Smith has two kg.\n"


def test_output_is_not_overwritten_without_force(tmp_path):
    from conftest import FakeEngine
    from spokenfile import SpokenFileError

    source = tmp_path / "notes.txt"
    source.write_text("2 kg\n", encoding="utf-8")
    output = tmp_path / "notes.spoken.txt"
    output.write_text("keep", encoding="utf-8")
    try:
        prepare_file(source, language="en", output=output, engine=FakeEngine())
    except SpokenFileError:
        pass
    else:
        raise AssertionError("expected existing output to be rejected")
    assert output.read_text(encoding="utf-8") == "keep"
    prepare_file(source, language="en", output=output, engine=FakeEngine(), force=True)
    assert output.read_text(encoding="utf-8") == "two kg\n"
