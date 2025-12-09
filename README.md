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

When conflicts are found:

```
These packages would FTBFS:
  jupyter-server: python3dist(jupyterlab) < 4.7

These packages would FTI:
  python3-jupyter-client-8.0.0-1.fc44: python3dist(jupyterlab) >= 4.0, < 4.7
```

- **FTBFS**: Fail To Build From Source (source packages that won't build)
- **FTI**: Fail To Install (binary packages that won't install)

## Exit Codes

- `0` - No conflicts detected
- `1` - Conflicts found or error occurred
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
