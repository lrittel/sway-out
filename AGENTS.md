# AGENTS.md

This file documents repository conventions and developer/agent workflows used by automated agents working on this project.
It is intended to be a concise, actionable reference for build, test and lint commands and for code-style and contribution guidelines.

**Project overview**
- Python package layout: sources live under `src/sway_out`.
- Minimum Python version: `3.12` (see `pyproject.toml`).
- Packaging uses `hatchling` and `uv` tooling (see `pyproject.toml`).

**Quick commands**
- Run application (development): `uv run sway-out` (Alternatively use `just app:run` which delegates to `uv`).
- Run full test suite: `uv run pytest` or `just tests:run`.
- Run a single test file: `uv run pytest tests/path/to/test_file.py`.
- Run a single test by nodeid: `uv run pytest tests/test_module.py::test_name`.
- Run linters/formatters via pre-commit: `uv run pre-commit run --all` or `just git:run-pre-commit-all`.
- Run linters one-off: `uv run black .`, `uv run isort .`.
- Build docs: `uv run mkdocs build` or `just docs:build`.

If `uv` is not available in the environment, use `python -m <tool>` with the tool installed in that environment (for example `python -m pytest`).

**CI workflows**
- CI workflows are found under `.github/workflows` (linting, testing, packaging, nix-flake support).
- Pre-commit is enforced and configured by `.pre-commit-config.yaml`; ensure pre-commit hooks are installed locally: `uv run pre-commit install`.

**How to run a single test (common developer/agent task)**
- From the repo root, run:
  - `uv run pytest tests/test_nothing.py` (run a file)
  - `uv run pytest tests/test_module.py::test_specific_case` (run single test case)
- You can pass `-k <expr>` or `-q -k` to filter tests by name. Use `-q` for quieter output.
- Pytest log level is configured in `pyproject.toml` (`log_cli_level = "DEBUG"`).

**Formatting and import order**
- Formatting: `black` (configured in `pyproject.toml`).
  - Default line length and options are the project defaults; rely on `black` for formatting decisions.
- Imports: `isort` with `profile = "black"` and `src_paths = ["src", "tests"]`.
  - Grouping order: Standard library -> Third-party -> Local (`src/`) imports.
  - Use explicit imports (avoid `from module import *`).
  - Keep import blocks sorted and separated by a single blank line between groups.

**Type hints and typing**
- The project targets Python 3.12+, prefer using modern typing features.
- Functions and methods should expose type annotations for public APIs.
- Use `typing` and `collections.abc` as appropriate. Prefer `list[str]`/`dict[str, int]` style (PEP 585) rather than `List[str]` where available.
- When returning `None`, annotate explicitly if it is part of the signature: `-> None`.
- Avoid overuse of `Any`. If `Any` is required, add a comment explaining why and where.

**Naming conventions**
- Modules, packages, and filenames: lowercase_with_underscores (snake_case).
- Functions and variables: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Classes: `CapWords` (PascalCase) — follow PEP8 class naming conventions.
- Private module-level symbols: prefix with a single underscore (e.g. `_helper`).
- Exception classes: end with `Error` (e.g. `LayoutValidationError`).

**Code organization**
- Keep library code under `src/sway_out`.
- Top-level module `__init__.py` should only expose the public API and minimal module-level logic.
- Avoid side-effects at import time (no heavy IO or subprocess calls in module scope).
- CLI entrypoint is `sway_out.main:main` as configured in `pyproject.toml` under `[project.scripts]`.

**Error handling**
- Prefer explicit exception classes for domain errors; define custom exceptions under `src/sway_out` when needed.
- Use exception chaining (`raise NewError(...) from exc`) when wrapping lower-level exceptions for context.
- Avoid bare `except:`; prefer `except Exception:` when catching broad runtime errors.
- Keep try/except blocks narrow and only around the operations that can fail.
- Log errors with context before re-raising if the error will be handled further up the stack.

**Logging**
- Use the standard library `logging` module.
- Create module-level logger: `logger = logging.getLogger(__name__)`.
- Do not configure root logging in library code — configuration belongs to the application entrypoint or tests.

**Testing**
- Tests live under `tests/` and use `pytest`.
- Test names should start with `test_` and reside in files named `test_*.py`.
- Keep tests deterministic and isolated; use fixtures rather than relying on shared mutable state.
- Use `pytest` markers sparingly and register any custom markers in `pyproject.toml` if needed.
- For async code use `pytest-asyncio` fixtures (already in `pyproject.toml` dev/test dependencies).

**Pre-commit and hooks**
- Project has `.pre-commit-config.yaml`. Hooks run `black`, `isort`, `uv-lock` and basic pre-commit hooks.
- Run the full pre-commit hook suite locally before pushing: `uv run pre-commit run --all`.
- Commit message validation is enforced via `commitizen` hook in `pre-commit` (commit-msg stage).

**Contribution workflow for agents**
- Make minimal, focused edits.
- Run `uv run pre-commit run` before proposing changes to avoid style failures.
- Do not change unrelated files.
- If adding or changing behavior, add or update tests in `tests/` to cover the behavior.
- When refactoring, prefer small, atomic commits (the repo uses `commitizen` for conventional commits).

**Imports & module-level patterns**
- Favor explicit relative imports within the package when appropriate, e.g. `from .layout import Layout` for sibling modules.
- For cross-package imports, use absolute imports starting from the package root: `from sway_out import utils`.

**Docstrings and documentation**
- Use triple-quoted docstrings for modules, classes, and public functions.
- Prefer Google-style or NumPy-style docstrings for public API; be consistent within a module.
- Update docs in `docs/reference/` when public API changes. The docs are built by `mkdocs` and `mkdocstrings`.

**Security and secrets**
- Never store secrets in the repository. Respect `.gitignore` and the `dist/` directory is ignored except for packages produced by the build.
- Use environment variables for configuration in CI and local development.

**Cursor/Copilot rules**
- This repository does not include `.cursor/rules/` or `.cursorrules` files.
- There is no `.github/copilot-instructions.md` file in this repository. If such files are added, include their contents and follow their rules; agents should reference them when present.

**Agent-specific notes**
- Agents may run commands via `uv` or call tools directly (e.g. `pytest`, `black`, `isort`). Prefer `uv run <tool>` so versions are consistent with `pyproject.toml` and the `uv` lock.
- When running shell commands, prefer the `Justfile` targets for common sequences (`just tests:run`, `just git:run-pre-commit`).
- Do not commit changes automatically unless explicitly requested.

**Making changes**
- When editing files, keep changes minimal and focused to one concern.
- Run the nearest tests that cover the changed code first (single test run described above).
- If a change affects formatting or imports, run `uv run isort` and `uv run black` and re-run pre-commit hooks.

**Troubleshooting**
- If tests fail locally but pass in CI, check environment differences (Python version, installed extras, uv lock). Use `uv run pip list` or `uv run python -V` to inspect.
- If linters disagree, run `uv run isort .` then `uv run black .` then `uv run pre-commit run --all`.

If anything in this file becomes outdated, update `AGENTS.md` near the change. Keep it concise and practical for automated agents.
