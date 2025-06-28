# Build the documentation.
[group('docs')]
build-docs:
    poetry run mkdocs build

# Serves the documentation on a local webserver.
[group('docs')]
serve-docs:
    poetry run mkdocs serve --watch ./src

# Runs the full test suite.
[group('tests')]
run-tests *PYTEST_FLAGS:
    poetry run pytest

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

# Run the pre-commit hook manually.
[group('ci')]
run-pre-commit:
    poetry run pre-commit run

# Run the pre-commit hook manually on all files.
run-pre-commit-all:
    poetry run pre-commit run --all

# Run the GitHub Actions workflows locally.
[group('ci')]
run-workflows:
    act
