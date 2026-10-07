from spokenfile import prepare_file


def test_markdown_skips_code_and_link_destination(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "notes.md"
    source.write_text(
        "# Chapter 2\n\nDr. Smith has **2 kg**. [Store 24](https://example.test/24)\n\n"
        "`2 kg`\n\n```python\nx = 2\n```\n",
        encoding="utf-8",
    )
    output = tmp_path / "notes.spoken.md"
    prepare_file(source, language="en", output=output, engine=FakeEngine())
    rendered = output.read_text(encoding="utf-8")
    assert "# Chapter two" in rendered
    assert "Doctor Smith has **two kg**" in rendered
    assert "[Store twenty four](https://example.test/24)" in rendered
    assert "`2 kg`" in rendered
    assert "x = 2" in rendered
