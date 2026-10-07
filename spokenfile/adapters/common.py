from __future__ import annotations

from dataclasses import dataclass


_UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True, slots=True)
class DecodedText:
    text: str
    encoding: str
    bom: bytes = b""

    def encode(self, text: str) -> bytes:
        return self.bom + text.encode(self.encoding)


def decode_utf8(data: bytes) -> DecodedText:
    if data.startswith(_UTF8_BOM):
        return DecodedText(data[len(_UTF8_BOM) :].decode("utf-8"), "utf-8", _UTF8_BOM)
    return DecodedText(data.decode("utf-8"), "utf-8")


def decode_htmlish(data: bytes) -> DecodedText:
    if data.startswith(_UTF8_BOM):
        return decode_utf8(data)
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return DecodedText(data.decode("utf-16"), "utf-16")
    # EPUB 3 XHTML is expected to be Unicode; the MVP intentionally rejects legacy
    # single-byte encodings rather than guessing and corrupting a publication.
    return DecodedText(data.decode("utf-8"), "utf-8")
