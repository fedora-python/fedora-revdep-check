# fedora-revdep-check

Check if updating a Fedora package will break reverse dependencies.

## Installation

```bash
pip install .
```

Requires `libdnf5` (system package, not from PyPI) and configured Fedora repositories.

## Usage

```bash
fedora-revdep-check <srpm-name> <new-version> [options]
```

### Examples

```bash
# Check rawhide (default)
fedora-revdep-check jupyterlab 4.7.0

# Verbose output
fedora-revdep-check pytest 8.0.0 --verbose

# Use stable Fedora instead of rawhide
fedora-revdep-check numpy 2.0.0 --repo fedora --repo fedora-source

# Check specific Fedora version
fedora-revdep-check python-requests 2.32.0 --repo fedora-40 --repo fedora-40-source
```

### Options

- `-v, --verbose` - Show detailed analysis
- `-r, --repo <repo-id>` - Repository to enable (can be specified multiple times, default: rawhide + rawhide-source)

## Output

When conflicts are found, they are categorized into new problems and already-broken packages:

```
These packages would FTBFS:
  jupyter-server: python3dist(jupyterlab) < 4.7

These packages would FTI:
  python3-jupyter-client-8.0.0-1.fc44: python3dist(jupyterlab) >= 4.0, < 4.7

These packages already FTBFS (not a new problem):
  some-package: python3dist(jupyterlab) < 3.0

These packages already FTI (not a new problem):
  python3-old-package-1.0.0-1.fc44: python3dist(jupyterlab) < 3.0
```

- **FTBFS**: Fail To Build From Source (source packages that won't build)
- **FTI**: Fail To Install (binary packages that won't install)

The tool distinguishes between:
- **New problems**: Packages that currently work but would break with the update
- **Already broken**: Packages that already fail with the current version in repos (not caused by the update)

## Exit Codes

- `0` - No new conflicts detected (already-broken packages don't cause non-zero exit)
- `1` - New conflicts found or error occurred
- `130` - Interrupted by user

## How It Works

1. Finds all binary packages built from the SRPM
2. Extracts their provides (excluding bundled)
3. Finds reverse dependencies for each provide
4. Filters to latest versions only (no duplicates)
5. Checks if the new version satisfies all requirements
6. Reports packages that would fail to build or install

Packages from the same SRPM are automatically excluded (they'll be updated together).

## Development

```bash
# Run tests
pytest

# Run tests for all Python versions
tox

# Lint
tox -e lint
```

## License

See LICENSE file.
