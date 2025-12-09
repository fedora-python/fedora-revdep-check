"""
Unit tests for dependency finding.

Tests the find_reverse_dependencies() method which queries for packages
that require a given provide.
"""

from fedora_revdep_check import FedoraRevDepChecker


class TestFindReverseDependencies:
    """Test find_reverse_dependencies() method."""

    def test_find_reverse_dependencies_with_rdeps(self, jupyterlab_base):
        """Test finding packages that require a provide."""
        checker = FedoraRevDepChecker(verbose=False, base=jupyterlab_base)

        rdeps = checker.find_reverse_dependencies('python3dist(jupyterlab)')

        assert len(rdeps) == 2
        rdep_names = {pkg.get_name() for pkg in rdeps}
        assert 'python3-jupyter-server' in rdep_names
        assert 'jupyter-server' in rdep_names
    
    def test_find_reverse_dependencies_no_rdeps(self, mock_dnf_base):
        """Test finding reverse dependencies when none exist."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

        rdeps = checker.find_reverse_dependencies('nonexistent-provide')

        assert rdeps == []
    
    def test_find_reverse_dependencies_pytest(self, mock_pytest_base):
        """Test finding reverse dependencies for pytest."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_pytest_base)

        rdeps = checker.find_reverse_dependencies('python3dist(pytest)')

        # Should find tox and pytest-xdist
        assert len(rdeps) == 2
        rdep_names = {pkg.get_name() for pkg in rdeps}
        # At least one of the dependent packages should be found
        assert 'python3-tox' in rdep_names
        assert 'python3-pytest-xdist' in rdep_names
