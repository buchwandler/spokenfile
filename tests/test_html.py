from spokenfile import prepare_file


def test_html_changes_text_nodes_but_not_attributes_or_code(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "page.html"
    source.write_text(
        '<p data-count="2">Dr. Smith has 2 kg.</p><code>2 kg</code><script>x=2</script>',
        encoding="utf-8",
    )
    output = tmp_path / "page.spoken.html"
    prepare_file(source, language="en", output=output, engine=FakeEngine())
    rendered = output.read_text(encoding="utf-8")
    assert 'data-count="2"' in rendered
    assert ">Doctor Smith has two kg.<" in rendered
    assert "<code>2 kg</code>" in rendered
    assert "<script>x=2</script>" in rendered
