#!/bin/sh
set -eu

# Run from any directory; the plugin folder lives beside this script.
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source_dir="prusa-xl-fix"
version=$(sed -n 's/^version = "\([^"]*\)".*/\1/p' "$source_dir/pyproject.toml")
case "$version" in
    ''|*[!A-Za-z0-9.+_-]*) echo "Invalid or missing package version" >&2; exit 1 ;;
esac
archive="octoprint_prusaxltoolfix-$version.tar.gz"

# COPYFILE_DISABLE prevents macOS from adding AppleDouble metadata.
COPYFILE_DISABLE=1 tar -czf "$archive" \
    --exclude='.DS_Store' \
    --exclude='._*' \
    --exclude='[Rr][Ee][Aa][Dd][Mm][Ee]*' \
    --exclude='tests' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.egg-info' \
    --exclude='.git' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='.ruff_cache' \
    "$source_dir"

printf 'Created %s\n' "$archive"
