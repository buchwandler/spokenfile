import zipfile

from spokenfile import prepare_file


def test_epub_patches_xhtml_and_preserves_other_members(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "book.epub"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", b"<container/>")
        archive.writestr("OEBPS/chapter.xhtml", b"<html><body><p>2 kg</p></body></html>")
        archive.writestr("OEBPS/image.bin", b"UNCHANGED")
    output = tmp_path / "book.spoken.epub"
    result = prepare_file(source, language="en", output=output, engine=FakeEngine())
    with zipfile.ZipFile(output) as archive:
        assert archive.read("mimetype") == b"application/epub+zip"
        assert b"two kg" in archive.read("OEBPS/chapter.xhtml")
        assert archive.read("OEBPS/image.bin") == b"UNCHANGED"
    assert result.format == "epub"
