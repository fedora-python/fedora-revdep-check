"""
Shared pytest fixtures and configuration for fedora-revdep-check tests.

This module provides fixtures that:
1. Mock libdnf5 module to prevent import errors during testing
2. Provide pre-configured mock DNF bases with test scenarios
3. Offer utilities for creating custom test packages
4. Capture stdout for output verification
"""

import sys
from unittest.mock import MagicMock
from io import StringIO
import pytest

# Mock libdnf5 module before importing fedora_revdep_check
# This prevents ImportError when libdnf5 is not installed
sys.modules['libdnf5'] = MagicMock()
sys.modules['libdnf5.base'] = MagicMock()
sys.modules['libdnf5.rpm'] = MagicMock()
sys.modules['libdnf5.repo'] = MagicMock()

# Now we can safely import test fixtures and the main module
from tests.fixtures.mock_packages import (  # noqa: E402
    MockBase,
    MockPackage,
    MockPackageQuery,
    MockRepoQuery,
    create_jupyterlab_scenario,
    create_pytest_scenario,
    create_rich_deps_scenario,
    create_bundled_provides_scenario,
    create_multi_binary_scenario,
    create_same_srpm_dependency_scenario,
    create_already_broken_scenario,
)
from fedora_revdep_check import FedoraRevDepChecker  # noqa: E402

# Patch libdnf5 classes to use our mocks
sys.modules['libdnf5'].rpm.Package = MockPackage
sys.modules['libdnf5'].rpm.PackageQuery = MockPackageQuery
sys.modules['libdnf5'].base.Base = MockBase
sys.modules['libdnf5'].repo.RepoQuery = MockRepoQuery


@pytest.fixture
def mock_dnf_base():
    """Provide a basic mock DNF base with no packages."""
    return MockBase()


@pytest.fixture
def mock_package_factory():
    """Provide a factory function for creating mock packages."""
    def create_package(**kwargs):
        """
        Create a mock package with default values.

        Args:
            **kwargs: Package attributes (name, version, release, etc.)

        Returns:
            MockPackage instance
        """
        defaults = {
            'name': 'test-package',
            'version': '1.0.0',
            'release': '1.fc40',
            'arch': 'noarch',
            'source_name': 'test-package',
            'epoch': '0',
            'provides': [],
            'requires': [],
        }
        defaults.update(kwargs)
        return MockPackage(**defaults)

    return create_package


@pytest.fixture
def jupyterlab_base():
    """Provide a mock DNF base with JupyterLab scenario (upgrade causes conflicts)."""
    return create_jupyterlab_scenario()


@pytest.fixture
def mock_pytest_base():
    """Provide a mock DNF base with pytest tool scenario (upgrade is compatible)."""
    return create_pytest_scenario()


@pytest.fixture
def rich_deps_base():
    """Provide a mock DNF base with rich dependencies scenario."""
    return create_rich_deps_scenario()


@pytest.fixture
def bundled_provides_base():
    """Provide a mock DNF base with bundled provides."""
    return create_bundled_provides_scenario()


@pytest.fixture
def multi_binary_base():
    """Provide a mock DNF base with multiple binary packages from one SRPM."""
    return create_multi_binary_scenario()


@pytest.fixture
def same_srpm_dep_base():
    """Provide a mock DNF base with packages from the same SRPM depending on each other."""
    return create_same_srpm_dependency_scenario()


@pytest.fixture
def already_broken_base():
    """Provide a mock DNF base with already-broken and new conflict scenarios."""
    return create_already_broken_scenario()


@pytest.fixture
def checker_instance(mock_dnf_base):
    """
    Provide a FedoraRevDepChecker instance with mocked DNF base.

    Args:
        mock_dnf_base: Mock DNF base fixture

    Returns:
        FedoraRevDepChecker instance ready for testing
    """
    return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)


@pytest.fixture
def verbose_checker_instance(mock_dnf_base):
    """
    Provide a verbose FedoraRevDepChecker instance with mocked DNF base.

    Args:
        mock_dnf_base: Mock DNF base fixture

    Returns:
        FedoraRevDepChecker instance with verbose=True
    """
    return FedoraRevDepChecker(verbose=True, base=mock_dnf_base)


@pytest.fixture
def capture_stdout(monkeypatch):
    """
    Capture stdout for output verification.

    Yields:
        StringIO object containing captured output

    Usage:
        def test_output(capture_stdout):
            print("test")
            assert "test" in capture_stdout.getvalue()
    """
    output = StringIO()
    monkeypatch.setattr('sys.stdout', output)
    yield output


@pytest.fixture
def capture_stderr(monkeypatch):
    """
    Capture stderr for error output verification.

    Yields:
        StringIO object containing captured error output
    """
    output = StringIO()
    monkeypatch.setattr('sys.stderr', output)
    yield output
