# Releasing spokenfile

`spokenfile` uses `setuptools-scm`; do not add a static `project.version` field.

Recommended release flow:

```bash
git status --short
python -m pytest
python -m ruff check .
git tag -s v0.1.0 -m "spokenfile 0.1.0"
python -m build
python -m twine check dist/*
```

The build must run from a Git checkout with tags available. The generated
`spokenfile/_version.py` is a build artifact and is ignored by Git.
