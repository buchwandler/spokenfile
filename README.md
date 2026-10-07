# spokenfile

`spokenfile` prepares ordinary files for text-to-speech while keeping the source file type.
It expands written forms such as numbers, dates, units, and abbreviations through `ttsready`,
then writes the spoken text back into a new file that can be opened and reviewed before TTS.

The MVP supports:

- UTF-8 plain text (`.txt`)
- Markdown (`.md`, `.markdown`)
- HTML (`.html`, `.htm`, `.xhtml`)
- EPUB (`.epub`) by patching HTML/XHTML members while preserving the EPUB container

PDF and DOCX are deliberately not part of this MVP. PDF needs a reflow policy and DOCX needs
run-aware OOXML mapping before either can offer a credible preservation guarantee.

## Architecture

```text
source file
   ↓
spokenfile adapter
   ↓
plain visible text units
   ↓
ttsready
   ↓
spoken changes / warnings
   ↓
spokenfile adapter
   ↓
same file type
```

`spokenfile` does not contain number or abbreviation rules. `ttsready` owns preparation and
`spokenform` remains the linguistic normalization backend below it.

## Install

```bash
python -m pip install -e .
```

The package uses `setuptools-scm`; versions are derived from Git metadata. Source trees without
Git metadata use the development fallback version configured in `pyproject.toml`.

## CLI

```bash
spokenfile formats
spokenfile inspect book.epub --language de
spokenfile prepare book.epub --language de
spokenfile prepare article.md --language en -o article.spoken.md --report changes.json
```

If `-o/--output` is omitted, `name.ext` becomes `name.spoken.ext`.

`inspect` performs the same preparation in memory but writes no converted file.

## Python API

```python
from spokenfile import prepare_file

result = prepare_file(
    "book.epub",
    language="de",
    output="book.spoken.epub",
)

print(result.changed)
for change in result.changes:
    print(change.source, "->", change.replacement)
```

## ttsready contract

This MVP targets the source-neutral `ttsready 0.2` API only. It calls
`ttsready.prepare_text()` with caller-owned unit IDs, language, role, protected spans, and
metadata. `spokenfile` owns file parsing and exact source-coordinate write-back; `ttsready`
never receives a source path and never opens or writes the file.

The old `ttsready 0.1.x` `Document`/`Section` compatibility bridge has intentionally been
removed. This keeps the dependency direction strict and makes a missing or incompatible
`ttsready` fail immediately instead of silently taking an SSMD-specific fallback path.

## Preservation rules

- Writes never modify the input file in place. Existing output files require explicit `--force`.
- Plain text preserves original bytes outside changed text spans, including line endings.
- Markdown uses a conservative source scanner and does not normalize fenced/indented code,
  inline code, link destinations, raw HTML-like lines, reference definitions, or front matter.
- HTML changes only text data outside `script`, `style`, `pre`, `code`, `noscript`, `svg`,
  `math`, and `textarea`. Attributes and markup are not rewritten.
- EPUB copies all ZIP entries and metadata, modifying only `.xhtml`, `.html`, and `.htm`
  members. A valid EPUB `mimetype` member is required.

The Markdown scanner is deliberately conservative rather than a complete CommonMark source-map
implementation. A future release should replace it with a parser/source-map adapter while keeping
the same adapter contract.
