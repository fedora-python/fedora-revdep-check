# fedora-revdep-check

Check if updating a Fedora package will break reverse dependencies.

## Installation

```bash
pip install .
```

Requires `libdnf5` (system package, not from PyPI) and configured Fedora repositories.

## Usage

### Check RPM files (recommended)

Check actual RPM files from a build before pushing to repositories:

```bash
fedora-revdep-check --rpms /path/to/build/*.rpm [options]
fedora-revdep-check --rpm-dir /path/to/build/RPMS/noarch/ [options]
```

This reads the actual provides from the RPM files, including their exact versions, which is more accurate than simulating version changes.

### Simulate version change (legacy mode)

Simulate updating a package to a new version:

```bash
fedora-revdep-check <srpm-name> <new-version> [options]
```

**Note**: This mode assumes all binary RPMs and their provides will have the same version, which may not always be accurate.

### Examples

```bash
# Check RPM files from a build (recommended)
fedora-revdep-check --rpms ~/rpmbuild/RPMS/noarch/*.rpm
fedora-revdep-check --rpm-dir ~/koji-download/python-sphinx-9.1.0-1.fc45/

# Legacy mode: simulate version change
fedora-revdep-check jupyterlab 4.7.0
fedora-revdep-check pytest 8.0.0 --verbose

# Use stable Fedora instead of rawhide
fedora-revdep-check --rpms *.rpm --repo fedora --repo fedora-source

# Check specific Fedora version
fedora-revdep-check python-requests 2.32.0 --repo fedora-40 --repo fedora-40-source
```

### Options

- `--rpms FILE [FILE ...]` - RPM file(s) to check
- `--rpm-dir DIR` - Directory containing RPM files to check
- `-v, --verbose` - Show detailed analysis
- `-r, --repo <repo-id>` - Repository to enable (can be specified multiple times, default: rawhide, rawhide-source, koji, and koji-source)

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

### RPM File Mode (Recommended)

1. Reads RPM files and extracts their provides with actual versions
2. Determines the source package name from the RPM headers
3. Finds reverse dependencies for each provide in Fedora repositories
4. Checks if each requirement would be satisfied by the provides in the RPM files
5. Reports packages that would fail to build or install

### Legacy Mode (Version Simulation)

1. Finds all binary packages built from the SRPM in repositories
2. Extracts their provides and simulates them with the new version
3. Finds reverse dependencies for each provide
4. Checks if the simulated new version satisfies all requirements
5. Reports packages that would fail to build or install

**Note**: Both modes automatically exclude packages from the same SRPM (they'll be updated together).

**Note**: Both modes distinguish between new conflicts and already-broken packages to avoid false positives.

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
