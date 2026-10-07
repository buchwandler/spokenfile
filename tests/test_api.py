import pytest

from spokenfile import UnsupportedFormatError, inspect_file, supported_formats
from spokenfile.api import default_output_path


def test_supported_formats():
    assert {".txt", ".md", ".html", ".epub"}.issubset(set(supported_formats()))


def test_default_output_path(tmp_path):
    source = tmp_path / "book.epub"
    assert default_output_path(source).name == "book.spoken.epub"


def test_unsupported_format(tmp_path):
    source = tmp_path / "book.pdf"
    source.write_bytes(b"%PDF")
    from conftest import FakeEngine

    with pytest.raises(UnsupportedFormatError):
        inspect_file(source, language="en", engine=FakeEngine())
