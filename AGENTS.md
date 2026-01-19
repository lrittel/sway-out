# AGENTS.md

This file documents repository conventions and workflows for automated agents in this project.
It provides actionable guidance for commands, coding style, CI configuration, and LSP/editor integration.

## Purpose

- Central reference for agent and developer workflows and best practices.
- Streamline commands, style enforcement, testing, and LSP/editor setup.

## Project Overview

- Python package layout: sources in `src/sway_out`.
- Minimum Python version: `3.12` (see `pyproject.toml`).
- Packaging via `hatchling` and `uv` tooling (see `pyproject.toml`).
- CLI entry point: `sway_out.main:main` (configured under `[project.scripts]`).

## Quick Commands

- List available recipes: `just --list`.
- Run development server: `just run` (alias for `uv run sway-out`).
- Run full test suite: `just run-tests` (decorates `uv run pytest`).
- Run single test file: `uv run pytest tests/path/to/test_file.py` (no Just recipe).
- Run specific test case: `uv run pytest tests/module.py::test_name` (nodeid runs bypass recipe).
- Run linters and formatters: `just run-pre-commit-all`.
- Run black only: `uv run black .` (or create a `just` recipe if needed).
- Run isort only: `uv run isort .` (or add a `just` recipe when helpful).
- Build docs: `just build-docs`.
- Serve docs locally: `just serve-docs` (watches `./src`).
- Run LSP/type checks: `just run-lsp` (delegates to `uv run basedpyright .`).
- Check environment: `uv run pip list && uv run python -V`.

## Formatting & Linting

- Formatting enforced with `black` (configured in `pyproject.toml`).
- Import sorting with `isort` (`profile = "black"`, `src_paths = ["src", "tests"]`).
- Pre-commit hooks installed via: `uv run pre-commit install`.
- Pre-commit config: `.pre-commit-config.yaml`.
- Run hooks manually: `uv run pre-commit run --all`.

## Import Order

- Group imports: standard library, third-party, local (`src/sway_out`), separated by a blank line; avoid `*` imports.

## Type Hints & Typing

- Target Python `3.12+`; prefer PEP 585 generics (`list[str]`, `dict[str, int]`).
- Annotate public functions and methods; explicit `-> None` when returning `None`.
- Avoid bare `Any`; document rationale when necessary.

## Naming Conventions

- Filenames and modules: `snake_case`.
- Functions and variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Private symbols: prefix with underscore (e.g. `_helper`).
- Exception classes: end with `Error`.

## Code Organization

- Library code under `src/sway_out/`; no side-effects on import.
- `__init__.py` exposes only public API.
- Use explicit relative imports for siblings and absolute imports for root modules.
- Keep module coupling minimal.

## Error Handling

- Define custom exception classes for domain errors.
- Use narrow `try/except` blocks around specific operations.
- Use `except Exception:` instead of bare `except:`.
- Chain exceptions: `raise NewError(...) from exc`.
- Log context before re-raising if handled upstream.

## Logging

- Use standard `logging` module; `logger = logging.getLogger(__name__)`.
- Configure handlers and levels in entrypoint or test setup; avoid root logger config in library code.

## Testing

- Tests in `tests/`, files named `test_*.py`, functions `test_*`.
- Use `pytest` and fixtures; avoid shared mutable state.
- For async code, use `pytest-asyncio` fixtures; filter tests with `-k` and quiet mode `-q`.
- Run nearest affected tests: `uv run pytest path/to/file.py`; ensure deterministic, isolated tests.

## Documentation

- Use triple-quoted docstrings for modules, classes, and public functions.
- Adopt Google or NumPy style consistently.
- Update reference docs under `docs/reference/` on API changes.
- Build docs: `uv run mkdocs build`; preview locally: `uv run mkdocs serve`.

## CI Workflows

- Configured in `.github/workflows/`.
- CI runs pre-commit hooks, `pytest`, and packaging with Nix-flake support.

## Pre-commit & Hooks

- Hooks in `.pre-commit-config.yaml`: black, isort, uv-lock, commitizen.
- Install hooks: `uv run pre-commit install`; run: `uv run pre-commit run --all`.
- Commit message validation via commitizen pre-commit hook (`commit-msg`).

## Branching & Commits

- Prefix branch names with issue number (e.g. `123-feature`).
- Use `commitizen` for conventional commits; validate via pre-commit hook.
- Do not amend pushed commits; create new commits if needed.
- Avoid destructive git commands without explicit approval.

## LSP Setup

- Recommended servers: `python-lsp-server` or `pyright`.
- Install Python LSP: `pip install "python-lsp-server[all]"`; install Pyright: `npm install -g pyright`.
- VSCode settings example:
  ```json
  {
      "python.languageServer": "Pylance",
      "python.formatting.provider": "black",
      "python.linting.enabled": true,
      "editor.formatOnSave": true
  }
  ```
- For other editors, enable LSP diagnostics, completion, and formatting plugins.

## Editor Integration

- Respect `.editorconfig`; enable format-on-save for black and isort.
- Configure debugger, live-reload, and encoding via editor plugins.

## Security & Secrets

- Do not commit secrets or credentials; respect `.gitignore`.
- Use environment variables for configuration.
- Treat `dist/` as output; ignore generated artifacts.

## Agent-specific Notes

- Prefer `uv run <tool>` for consistency with lock file and `just` targets.
- Make atomic edits; avoid touching unrelated files.
- After edits, run nearest tests: `uv run pytest path/to/file.py`.
- Run pre-commit hooks locally before proposing changes.

## Troubleshooting

- If tests pass in CI but fail locally, check Python version: `uv run python -V`.
- Compare dependencies: `uv run pip list`.
- Fix formatting: `uv run isort . && uv run black . && uv run pre-commit run --all`.
- Verify lock file consistency if packaging errors occur.
- Open an issue for persistent failures or unclear errors.
