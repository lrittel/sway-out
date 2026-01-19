# Run the application.
[group('app')]
run *args:
    uv run sway-out {{ args }}

# Build the documentation.
[group('docs')]
build-docs:
    uv run mkdocs build

# Serves the documentation on a local webserver.
[group('docs')]
serve-docs:
    uv run mkdocs serve --watch ./src

# Runs the full test suite.
[group('tests')]
run-tests *PYTEST_FLAGS:
    uv run pytest

# Runs the full test suite whenever a file changes.
[group('tests')]
watch-tests *PYTEST_FLAGS:
    #!/usr/bin/env bash
    # 2 is the return value when a new file was added.
    while true; do
        fd -e py | entr -cd just run-tests
        if [ "$?" -ne 2 ] ; then
            break
        fi
        sleep 0.5
    done

# Run cz to create a new commit interactively.
[group('git')]
commit *args:
    uv run cz commit {{ args }}

# Run the pre-commit utility.
[group('checks')]
pre-commit *args:
    uv run pre-commit {{ args }}

# Run the pre-commit hook manually.
[group('checks')]
run-pre-commit:
    uv run pre-commit run

# Run the pre-commit hook manually on all files.
[group('checks')]
run-pre-commit-all:
    uv run pre-commit run --all

# Get basedpyright diagnostics for all files.
[group('checks')]
run-lsp:
    uv run basedpyright .

# List all available workflows.
[group('ci')]
list-workflows:
    act --list

# Run all workflows.
[group('ci')]
run-all-workflows *act_args:
    act {{ act_args }}

# Run a specific workflow (see list-workflows).
[group('ci')]
run-workflow name *act_args:
    act --job "{{ name }}" {{ act_args }}
