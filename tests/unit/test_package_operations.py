"""
Unit tests for package operations.

Tests get_binary_packages() and get_provides() methods which query
and parse package information.
"""

import pytest
from fedora_revdep_check import FedoraRevDepChecker
from tests.fixtures.mock_packages import MockPackage, MockBase


class TestGetBinaryPackages:
    """Test get_binary_packages() method."""

    
    def test_get_binary_packages_valid_srpm(self, jupyterlab_base):
        """Test getting binary packages from a valid SRPM."""
        checker = FedoraRevDepChecker(verbose=False, base=jupyterlab_base)
        packages = checker.get_binary_packages('jupyterlab')

        assert len(packages) == 1
        assert packages[0].get_name() == 'python3-jupyterlab'
        assert packages[0].get_source_name() == 'jupyterlab'

    
    def test_get_binary_packages_nonexistent_srpm(self, mock_dnf_base):
        """Test getting packages from non-existent SRPM returns empty list."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_dnf_base)
        packages = checker.get_binary_packages('nonexistent-package')

        assert packages == []

    
    def test_get_binary_packages_filters_source_packages(self):
        """Test that source packages (arch='src') are filtered out."""
        packages_list = [
            MockPackage(
                name='foo',
                version='1.0.0',
                release='1.fc40',
                arch='noarch',
                source_name='foo',
            ),
            MockPackage(
                name='foo',
                version='1.0.0',
                release='1.fc40',
                arch='src',  # Source package - should be filtered
                source_name='foo',
            ),
        ]
        base = MockBase(packages=packages_list)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        result = checker.get_binary_packages('foo')

        assert len(result) == 1
        assert result[0].get_arch() == 'noarch'
        assert result[0].get_arch() != 'src'

    
    def test_get_binary_packages_multiple_binaries(self, multi_binary_base):
        """Test getting multiple binary packages from one SRPM."""
        checker = FedoraRevDepChecker(verbose=False, base=multi_binary_base)
        packages = checker.get_binary_packages('python-requests')

        # Should get both python3-requests and python3-requests-doc
        assert len(packages) == 2
        names = {pkg.get_name() for pkg in packages}
        assert 'python3-requests' in names
        assert 'python3-requests-doc' in names

        # All should have same source
        for pkg in packages:
            assert pkg.get_source_name() == 'python-requests'

    
    def test_get_binary_packages_deduplication(self):
        """Test that duplicate packages are deduplicated by NEVRA."""
        # Create scenario with duplicate packages
        packages_list = [
            MockPackage(
                name='foo',
                version='1.0.0',
                release='1.fc40',
                arch='noarch',
                source_name='foo',
                epoch='0',
            ),
            MockPackage(
                name='foo',
                version='1.0.0',
                release='1.fc40',
                arch='noarch',
                source_name='foo',
                epoch='0',
            ),  # Duplicate
        ]
        base = MockBase(packages=packages_list)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        result = checker.get_binary_packages('foo')

        # Should only get one despite duplicates
        assert len(result) == 1


class TestGetProvides:
    """Test get_provides() method."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    
    def test_get_provides_simple(self, checker):
        """Test parsing simple provides without versions."""
        pkg = MockPackage(
            name='foo',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='foo',
            provides=['foo']
        )

        provides = checker.get_provides(pkg)

        assert len(provides) == 1
        assert provides[0] == ('foo', None, 'foo')

    
    def test_get_provides_with_version(self, checker):
        """Test parsing provides with version constraints."""
        pkg = MockPackage(
            name='foo',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='foo',
            provides=[
                'foo = 1.0.0',
                'python3dist(foo) = 1.0.0',
            ]
        )

        provides = checker.get_provides(pkg)

        assert len(provides) == 2
        # Find each provide
        foo_prov = next(p for p in provides if p[0] == 'foo')
        pydist_prov = next(p for p in provides if p[0] == 'python3dist(foo)')

        assert foo_prov == ('foo', '1.0.0', 'foo = 1.0.0')
        assert pydist_prov == ('python3dist(foo)', '1.0.0', 'python3dist(foo) = 1.0.0')

    
    def test_get_provides_filters_bundled(self, checker, bundled_provides_base):
        """Test that bundled provides are filtered out."""
        # Get the package from the base
        pkg = list(bundled_provides_base._packages)[0]

        provides = checker.get_provides(pkg)

        # Should get myapp provides but NOT bundled ones
        provide_names = {p[0] for p in provides}
        assert 'myapp' in provide_names
        assert 'bundled(libfoo)' not in provide_names
        assert 'bundled(libbar)' not in provide_names

    
    def test_get_provides_various_formats(self, checker):
        """Test parsing provides in various formats."""
        pkg = MockPackage(
            name='test',
            version='1.0.0',
            release='1.fc40',
            arch='x86_64',
            source_name='test',
            provides=[
                'test',
                'test = 1.0.0',
                'test >= 1.0.0',
                'test(x86-64)',
                'test(x86-64) = 1.0.0',
                'python3dist(test)',
                'python3dist(test) = 1.0.0',
            ]
        )

        provides = checker.get_provides(pkg)

        # All should be parsed
        assert len(provides) == 7

        # Check that versions are correctly extracted
        versioned = [p for p in provides if p[1] is not None]
        assert len(versioned) == 4  # Four have versions

    
    def test_get_provides_empty(self, checker):
        """Test package with no provides returns empty list."""
        pkg = MockPackage(
            name='empty',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='empty',
            provides=[]
        )

        provides = checker.get_provides(pkg)

        assert provides == []

    
    def test_get_provides_python_dist_format(self, checker):
        """Test python3dist() provides are parsed correctly."""
        pkg = MockPackage(
            name='python3-pytest',
            version='7.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='pytest',
            provides=[
                'python3dist(pytest) = 7.0.0',
                'python3dist(pytest) >= 7.0.0',
            ]
        )

        provides = checker.get_provides(pkg)

        assert len(provides) == 2
        # Both should have the full name including parentheses
        for prov in provides:
            assert prov[0] == 'python3dist(pytest)'
            assert prov[1] == '7.0.0'
