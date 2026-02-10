"""
Mock DNF objects and test package scenarios.

This module provides fake implementations of libdnf5 classes for testing
without requiring real DNF repositories. All mocks are designed to simulate
the actual behavior of libdnf5 objects while being predictable and fast.
"""

from typing import List, Optional


class MockProvide:
    """Mock libdnf5 Provide object."""

    def __init__(self, provide_str: str):
        """
        Initialize a mock provide.

        Args:
            provide_str: Full provide string (e.g., "python3dist(pytest) >= 7.0.0")
        """
        self._provide_str = provide_str

    def to_string(self) -> str:
        """Return the provide string."""
        return self._provide_str


class MockRequire:
    """Mock libdnf5 Require object."""

    def __init__(self, require_str: str):
        """
        Initialize a mock requirement.

        Args:
            require_str: Full requirement string (e.g., "python3dist(pytest) >= 7.0.0")
        """
        self._require_str = require_str

    def to_string(self) -> str:
        """Return the requirement string."""
        return self._require_str


class MockPackage:
    """Mock libdnf5.rpm.Package object."""

    def __init__(
        self,
        name: str,
        version: str,
        release: str,
        arch: str,
        source_name: str,
        epoch: str = '0',
        provides: Optional[List[str]] = None,
        requires: Optional[List[str]] = None
    ):
        """
        Initialize a mock package.

        Args:
            name: Package name
            version: Package version
            release: Package release
            arch: Package architecture (e.g., 'x86_64', 'noarch', 'src')
            source_name: Source package name
            epoch: Package epoch (default '0')
            provides: List of provide strings
            requires: List of requirement strings
        """
        self._name = name
        self._version = version
        self._release = release
        self._arch = arch
        self._source_name = source_name
        self._epoch = epoch
        self._provides = [MockProvide(p) for p in (provides or [])]
        self._requires = [MockRequire(r) for r in (requires or [])]

    def get_name(self) -> str:
        return self._name

    def get_version(self) -> str:
        return self._version

    def get_release(self) -> str:
        return self._release

    def get_arch(self) -> str:
        return self._arch

    def get_source_name(self) -> str:
        return self._source_name

    def get_epoch(self) -> str:
        return self._epoch

    def get_provides(self) -> List[MockProvide]:
        return self._provides

    def get_requires(self) -> List[MockRequire]:
        return self._requires


class MockPackageQuery:
    """Mock libdnf5.rpm.PackageQuery object."""

    def __init__(self, base, packages: Optional[List[MockPackage]] = None):
        """
        Initialize a mock package query.

        Args:
            base: Mock DNF base object
            packages: Optional list of packages (if None, uses base.packages)
        """
        self._base = base
        self._packages = packages if packages is not None else list(base._packages)
        self._filtered_packages = list(self._packages)

    def __iter__(self):
        """Iterate over filtered packages."""
        return iter(self._filtered_packages)

    def filter_name(self, names: List[str]):
        """Filter packages by name."""
        self._filtered_packages = [
            pkg for pkg in self._filtered_packages
            if pkg.get_name() in names
        ]

    def filter_latest_evr(self):
        """Filter to keep only latest EVR (epoch:version-release)."""
        # For simplicity, this mock just keeps the current filtered set
        # In real tests, packages should be pre-filtered
        pass

    def filter_requires(self, requires: List[str]):
        """Filter packages that require the given provides."""
        filtered = []
        for pkg in self._filtered_packages:
            for req in pkg.get_requires():
                req_str = req.to_string()
                # Check if any of the required provides match
                for required_name in requires:
                    if required_name in req_str:
                        filtered.append(pkg)
                        break
        self._filtered_packages = filtered


class MockRepo:
    """Mock repository object."""

    def __init__(self, repo_id: str):
        """Initialize a mock repository."""
        self._id = repo_id
        self._enabled = False

    def get_id(self) -> str:
        return self._id

    def enable(self):
        """Enable the repository."""
        self._enabled = True

    def disable(self):
        """Disable the repository."""
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled


class MockRepoQuery:
    """Mock libdnf5.repo.RepoQuery object."""

    def __init__(self, base_or_query):
        """Initialize mock repo query from base or another query."""
        if isinstance(base_or_query, MockRepoQuery):
            # Copy constructor
            self._repos = list(base_or_query._repos)
            self._filtered_repos = list(base_or_query._filtered_repos)
        else:
            # From base
            self._repos = list(base_or_query._repos)
            self._filtered_repos = list(self._repos)

    def __iter__(self):
        """Iterate over filtered repositories."""
        return iter(self._filtered_repos)

    def filter_id(self, repo_id: str):
        """Filter repositories by ID."""
        self._filtered_repos = [
            repo for repo in self._filtered_repos
            if repo.get_id() == repo_id
        ]


class MockRepoSack:
    """Mock repository sack."""

    def __init__(self, repos: List[MockRepo]):
        """Initialize mock repo sack."""
        self._repos = repos

    def create_repos_from_system_configuration(self):
        """Mock creating repos from system config (no-op)."""
        pass

    def load_repos(self):
        """Mock loading repository metadata (no-op)."""
        pass


class MockVars:
    """Mock DNF variables."""

    def __init__(self):
        """Initialize mock vars."""
        self._vars = {}

    def set(self, key: str, value: str):
        """Set a variable."""
        self._vars[key] = value

    def get(self, key: str) -> Optional[str]:
        """Get a variable."""
        return self._vars.get(key)


class MockBase:
    """Mock libdnf5.base.Base object."""

    def __init__(self, packages: Optional[List[MockPackage]] = None, repos: Optional[List[MockRepo]] = None):
        """
        Initialize a mock DNF base.

        Args:
            packages: List of mock packages available in the base
            repos: List of mock repositories
        """
        self._packages = packages or []
        self._repos = repos or [
            MockRepo('rawhide'),
            MockRepo('rawhide-source'),
            MockRepo('koji'),
            MockRepo('koji-source'),
        ]
        self._vars = MockVars()
        self._repo_sack = MockRepoSack(self._repos)

    def get_vars(self) -> MockVars:
        """Get DNF variables."""
        return self._vars

    def get_repo_sack(self) -> MockRepoSack:
        """Get repository sack."""
        return self._repo_sack

    def setup(self):
        """Mock setup (no-op)."""
        pass


# Test package scenarios

def create_jupyterlab_scenario():
    """
    Create a JupyterLab test scenario where upgrading causes conflicts.

    Scenario:
    - jupyterlab 4.6.0 currently installed
    - jupyter-server requires jupyterlab < 4.7
    - Upgrading to 4.7.0 would break jupyter-server
    """
    packages = [
        # JupyterLab packages (from SRPM 'jupyterlab')
        MockPackage(
            name='python3-jupyterlab',
            version='4.6.0',
            release='1.fc40',
            arch='noarch',
            source_name='jupyterlab',
            provides=[
                'python3-jupyterlab',
                'python3-jupyterlab = 4.6.0-1.fc40',
                'python3dist(jupyterlab) = 4.6.0',
            ]
        ),
        # Jupyter Server (depends on jupyterlab)
        MockPackage(
            name='python3-jupyter-server',
            version='2.10.0',
            release='1.fc40',
            arch='noarch',
            source_name='jupyter-server',
            requires=[
                '(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 4.7)',
            ]
        ),
        # Jupyter Server SRPM (for FTBFS testing)
        MockPackage(
            name='jupyter-server',
            version='2.10.0',
            release='1.fc40',
            arch='src',
            source_name='jupyter-server',
            requires=[
                '(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 4.7)',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_pytest_scenario():
    """
    Create a pytest test scenario where upgrading is compatible.

    Scenario:
    - pytest 7.0.0 currently installed
    - tox requires pytest >= 6.0
    - Upgrading to 7.1.0 is compatible
    """
    packages = [
        # Pytest packages (from SRPM 'pytest')
        MockPackage(
            name='python3-pytest',
            version='7.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='pytest',
            provides=[
                'python3-pytest',
                'python3-pytest = 7.0.0-1.fc40',
                'python3dist(pytest) = 7.0.0',
                'pytest',
            ]
        ),
        # Tox (depends on pytest)
        MockPackage(
            name='python3-tox',
            version='4.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='tox',
            requires=[
                'python3dist(pytest) >= 6.0',
            ]
        ),
        # Pytest-xdist (for false positive testing)
        MockPackage(
            name='python3-pytest-xdist',
            version='3.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='pytest-xdist',
            provides=[
                'python3-pytest-xdist',
                'python3dist(pytest-xdist) = 3.0.0',
            ],
            requires=[
                'python3dist(pytest) >= 7.0',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_rich_deps_scenario():
    """
    Create a scenario with rich dependencies.

    Scenario:
    - foo 2.5.0 currently installed
    - bar requires (foo >= 2.0 with foo < 3.0)
    - Upgrading to 3.0.0 would break bar
    """
    packages = [
        # Foo packages
        MockPackage(
            name='foo',
            version='2.5.0',
            release='1.fc40',
            arch='x86_64',
            source_name='foo',
            provides=[
                'foo',
                'foo = 2.5.0-1.fc40',
                'foo(x86-64) = 2.5.0-1.fc40',
            ]
        ),
        # Bar (depends on foo with rich dependency)
        MockPackage(
            name='bar',
            version='1.0.0',
            release='1.fc40',
            arch='x86_64',
            source_name='bar',
            requires=[
                '(foo >= 2.0 with foo < 3.0)',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_bundled_provides_scenario():
    """
    Create a scenario with bundled provides that should be filtered.

    Scenario:
    - Package with bundled dependencies that should not trigger false positives
    """
    packages = [
        # Package with bundled provides
        MockPackage(
            name='myapp',
            version='1.0.0',
            release='1.fc40',
            arch='x86_64',
            source_name='myapp',
            provides=[
                'myapp',
                'myapp = 1.0.0',
                'bundled(libfoo) = 1.2.3',
                'bundled(libbar) = 2.0.0',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_multi_binary_scenario():
    """
    Create a scenario with multiple binary packages from one SRPM.

    Scenario:
    - python-requests SRPM produces python3-requests and python3-requests-doc
    - Each has different provides
    """
    packages = [
        # Main package
        MockPackage(
            name='python3-requests',
            version='2.31.0',
            release='1.fc40',
            arch='noarch',
            source_name='python-requests',
            provides=[
                'python3-requests',
                'python3-requests = 2.31.0-1.fc40',
                'python3dist(requests) = 2.31.0',
            ]
        ),
        # Documentation package
        MockPackage(
            name='python3-requests-doc',
            version='2.31.0',
            release='1.fc40',
            arch='noarch',
            source_name='python-requests',
            provides=[
                'python3-requests-doc',
                'python3-requests-doc = 2.31.0-1.fc40',
            ]
        ),
        # Dependent package
        MockPackage(
            name='python3-some-client',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='some-client',
            requires=[
                'python3dist(requests) >= 2.30',
                'python3dist(requests) < 3',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_same_srpm_dependency_scenario():
    """
    Create a scenario where binary packages from the same SRPM depend on each other.

    Scenario (like micropipenv):
    - micropipenv SRPM produces micropipenv and micropipenv+toml
    - micropipenv+toml requires micropipenv
    - This should NOT be flagged as a conflict when updating micropipenv
    """
    packages = [
        # Base package
        MockPackage(
            name='micropipenv',
            version='1.10.0',
            release='1.fc40',
            arch='noarch',
            source_name='micropipenv',
            provides=[
                'micropipenv',
                'micropipenv = 1.10.0-1.fc40',
                'python3dist(micropipenv) = 1.10.0',
            ]
        ),
        # Extra package with dependencies on base package
        MockPackage(
            name='micropipenv+toml',
            version='1.10.0',
            release='1.fc40',
            arch='noarch',
            source_name='micropipenv',  # Same SRPM!
            provides=[
                'micropipenv+toml',
                'micropipenv+toml = 1.10.0-1.fc40',
                'python3dist(micropipenv[toml]) = 1.10.0',
            ],
            requires=[
                'python3dist(micropipenv) = 1.10.0',  # Requires the base package
            ]
        ),
        # External package that depends on micropipenv
        MockPackage(
            name='python3-external-tool',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='external-tool',
            requires=[
                'python3dist(micropipenv) >= 1.9',
                'python3dist(micropipenv) < 1.12',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_already_broken_scenario():
    """
    Create a scenario with both new conflicts and already-broken packages.

    Scenario:
    - library 4.0.0 currently installed
    - old-package requires library < 3.0 (already broken with current 4.0.0)
    - new-package requires library < 5.0 (will break when upgrading to 5.0.0)
    """
    packages = [
        # Library package
        MockPackage(
            name='library',
            version='4.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='library',
            provides=[
                'library',
                'library = 4.0.0-1.fc40',
                'python3dist(library) = 4.0.0',
            ]
        ),
        # Old package (already broken)
        MockPackage(
            name='python3-old-package',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='old-package',
            requires=[
                'python3dist(library) < 3.0',  # Already fails with 4.0.0
            ]
        ),
        # Old package SRPM (for FTBFS testing)
        MockPackage(
            name='old-package',
            version='1.0.0',
            release='1.fc40',
            arch='src',
            source_name='old-package',
            requires=[
                'python3dist(library) < 3.0',  # Already fails with 4.0.0
            ]
        ),
        # New package (will break with 5.0.0)
        MockPackage(
            name='python3-new-package',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='new-package',
            requires=[
                'python3dist(library) < 5.0',  # Will fail with 5.0.0
            ]
        ),
        # New package SRPM (for FTBFS testing)
        MockPackage(
            name='new-package',
            version='1.0.0',
            release='1.fc40',
            arch='src',
            source_name='new-package',
            requires=[
                'python3dist(library) < 5.0',  # Will fail with 5.0.0
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_epoch_package_scenario():
    """
    Create a scenario with packages that have epochs.

    Scenario:
    - sphinx 1:8.0.0 currently installed (epoch 1)
    - reverse-dep requires sphinx >= 1:8.0.0
    - Upgrading to 9.0.0 without specifying epoch should inherit epoch 1
    - So 1:9.0.0 should satisfy the requirement (not 0:9.0.0 which would fail)
    """
    packages = [
        # Sphinx package with epoch 1
        MockPackage(
            name='python3-sphinx',
            version='8.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='sphinx',
            epoch='1',
            provides=[
                'python3-sphinx',
                'python3-sphinx = 1:8.0.0-1.fc40',
                'python3dist(sphinx) = 8.0.0',
            ]
        ),
        # Reverse dependency requiring >= 1:8.0.0
        MockPackage(
            name='python3-docs',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='python-docs',
            requires=[
                'python3-sphinx >= 1:8.0.0',
            ]
        ),
    ]

    return MockBase(packages=packages)


def create_epoch_with_dist_provides_scenario():
    """
    Create a scenario with packages that have both RPM and dist provides.

    Scenario:
    - sphinx 1:8.0.0 currently installed (epoch 1)
    - Provides both python3-sphinx (with epoch) and python3dist(sphinx) (without epoch)
    - reverse-dep-rpm requires python3-sphinx >= 1:8.0.0 (RPM provide with epoch)
    - reverse-dep-dist requires python3dist(sphinx) < 10~~ (dist provide without epoch)
    - Upgrading to 9.1.0 should satisfy both (use epoch for RPM, not for dist)
    """
    packages = [
        # Sphinx package with epoch 1
        MockPackage(
            name='python3-sphinx',
            version='8.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='sphinx',
            epoch='1',
            provides=[
                'python3-sphinx',
                'python3-sphinx = 1:8.0.0-1.fc40',
                'python3dist(sphinx) = 8.0.0',
            ]
        ),
        # Reverse dependency requiring RPM package with epoch
        MockPackage(
            name='python3-docs',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='python-docs',
            requires=[
                'python3-sphinx >= 1:8.0.0',
            ]
        ),
        # Reverse dependency requiring dist provide without epoch
        MockPackage(
            name='python3-myst-parser',
            version='5.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='python-myst-parser',
            requires=[
                'python3dist(sphinx) < 10~~',
            ]
        ),
    ]

    return MockBase(packages=packages)
