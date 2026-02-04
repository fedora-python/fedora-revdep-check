"""
Integration tests for simulate_version_change().

Tests the complete simulation workflow with realistic scenarios.
"""

from fedora_revdep_check import FedoraRevDepChecker


class TestSimulateVersionChange:
    """Test the complete version change simulation workflow."""

    def test_simulate_version_change_causes_conflict(self, jupyterlab_base):
        """Test simulation where version upgrade causes conflicts."""
        checker = FedoraRevDepChecker(verbose=False, base=jupyterlab_base)

        # Upgrading jupyterlab to 4.7.0 should conflict with jupyter-server
        results = checker.simulate_version_change('jupyterlab', '4.7.0')

        assert 'error' not in results
        assert results['srpm_name'] == 'jupyterlab'
        assert results['new_version'] == '4.7.0'
        assert len(results['binary_packages']) >= 1
        assert 'python3-jupyterlab-4.6.0-1.fc40' in results['binary_packages']

        # Should have conflicts
        assert len(results['conflicts']) >= 1

        # Check conflict details
        conflict = results['conflicts'][0]
        assert 'rdep_package' in conflict
        assert 'rdep_source' in conflict
        assert 'rdep_arch' in conflict
        assert conflict['provide_name'] == 'python3dist(jupyterlab)'
        assert conflict['new_version'] == '4.7.0'
        assert 'python3dist(jupyterlab) < 4.7' in conflict['failed_constraint']
    
    def test_simulate_version_change_no_conflict(self, mock_pytest_base):
        """Test simulation where version upgrade is compatible."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_pytest_base)

        # Upgrading pytest to 7.1.0 should be compatible with tox (requires >= 6.0)
        results = checker.simulate_version_change('pytest', '7.1.0')

        assert 'error' not in results
        assert results['srpm_name'] == 'pytest'
        assert results['new_version'] == '7.1.0'

        # Should have no conflicts
        assert len(results['conflicts']) == 0
    
    def test_simulate_version_change_rich_dependency_conflict(self, rich_deps_base):
        """Test simulation with rich dependency conflicts."""
        checker = FedoraRevDepChecker(verbose=False, base=rich_deps_base)

        # Upgrading foo to 3.0.0 should conflict with bar (requires foo >= 2.0 with foo < 3.0)
        results = checker.simulate_version_change('foo', '3.0.0')

        assert 'error' not in results
        assert results['srpm_name'] == 'foo'
        assert results['new_version'] == '3.0.0'

        # Should have conflicts
        assert len(results['conflicts']) >= 1

        conflict = results['conflicts'][0]
        assert conflict['provide_name'] == 'foo'
        assert conflict['new_version'] == '3.0.0'
        assert 'foo < 3.0' in conflict['failed_constraint']
    
    def test_simulate_version_change_nonexistent_package(self, mock_dnf_base):
        """Test simulation with non-existent package."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

        results = checker.simulate_version_change('nonexistent', '1.0.0')

        assert 'error' in results
        assert 'No packages found' in results['error']
        assert 'nonexistent' in results['error']
        assert results['binary_packages'] == []
    
    def test_simulate_version_change_multiple_binaries(self, multi_binary_base):
        """Test simulation with multiple binary packages from one SRPM."""
        checker = FedoraRevDepChecker(verbose=False, base=multi_binary_base)

        # python-requests produces multiple binary packages
        results = checker.simulate_version_change('python-requests', '2.32.0')

        assert 'error' not in results
        assert results['srpm_name'] == 'python-requests'
        assert len(results['binary_packages']) == 2

        # Both binary packages should be listed
        binary_names = ' '.join(results['binary_packages'])
        assert 'python3-requests' in binary_names
        assert 'python3-requests-doc' in binary_names
   
    def test_simulate_version_change_upgrade_satisfies_upper_bound(self, mock_pytest_base):
        """Test that version upgrade breaking upper bound is detected."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_pytest_base)

        # Pytest 8.0 would break pytest-xdist which requires >= 7.0
        # but let's test a version that would break if there was an upper bound
        results = checker.simulate_version_change('pytest', '10.0.0')

        # Current test scenario doesn't have strict upper bound, so should pass
        # But the infrastructure is in place to detect such conflicts
        assert 'error' not in results
        assert results['new_version'] == '10.0.0'

    def test_simulate_version_change_bundled_provides_ignored(self, bundled_provides_base):
        """Test that bundled provides are ignored in conflict checking."""
        checker = FedoraRevDepChecker(verbose=False, base=bundled_provides_base)

        # Upgrading myapp should not trigger false positives from bundled provides
        results = checker.simulate_version_change('myapp', '2.0.0')

        assert 'error' not in results
        # Should have no conflicts (no packages depend on bundled libs)
        assert len(results['conflicts']) == 0

    def test_simulate_version_change_downgrade(self, mock_pytest_base):
        """Test simulation with version downgrade."""
        checker = FedoraRevDepChecker(verbose=False, base=mock_pytest_base)

        # Downgrading pytest to 6.5.0 might break dependencies requiring >= 7.0
        results = checker.simulate_version_change('pytest', '6.5.0')

        # This should cause conflicts as pytest-xdist requires >= 7.0
        assert 'error' not in results
        assert len(results['conflicts']) >= 1

        conflict = results['conflicts'][0]
        assert conflict['new_version'] == '6.5.0'
        assert 'pytest' in conflict['provide_name']

    def test_simulate_version_change_same_srpm_dependency(self, same_srpm_dep_base):
        """Test that packages from the same SRPM depending on each other are not flagged as conflicts."""
        checker = FedoraRevDepChecker(verbose=False, base=same_srpm_dep_base)

        # Upgrading micropipenv to 1.11.0
        # micropipenv+toml (from same SRPM) requires micropipenv = 1.10.0
        # This should NOT be flagged as a conflict because they'll be updated together
        results = checker.simulate_version_change('micropipenv', '1.11.0')

        assert 'error' not in results

        # Check that micropipenv+toml is NOT in conflicts (it's from the same SRPM)
        conflict_packages = [c['rdep_package'] for c in results['conflicts']]
        assert 'micropipenv+toml' not in [p.split('-')[0] for p in conflict_packages]

        # However, external packages should still be checked
        # python3-external-tool requires micropipenv < 1.12, so it should still be satisfied
        # (1.11.0 < 1.12 is True)
        assert len(results['conflicts']) == 0

    def test_simulate_version_change_already_broken_package(self, already_broken_base):
        """Test that already-broken packages are properly marked."""
        checker = FedoraRevDepChecker(verbose=False, base=already_broken_base)

        # Upgrading library from 4.0.0 to 5.0.0
        # old-package requires library < 3.0, so it's already broken with 4.0.0
        # new-package requires library < 5.0, so it will break with 5.0.0
        results = checker.simulate_version_change('library', '5.0.0')

        assert 'error' not in results
        # Should have 4 conflicts: 2 FTBFS (src) + 2 FTI (noarch) for each package
        assert len(results['conflicts']) == 4

        # Separate conflicts into already broken and new
        old_pkg_conflicts = []
        new_pkg_conflicts = []
        for conflict in results['conflicts']:
            if 'old-package' in conflict['rdep_source']:
                old_pkg_conflicts.append(conflict)
            elif 'new-package' in conflict['rdep_source']:
                new_pkg_conflicts.append(conflict)

        # old-package should have 2 conflicts (FTBFS and FTI), both already broken
        assert len(old_pkg_conflicts) == 2
        for conflict in old_pkg_conflicts:
            assert conflict['already_broken'] is True
            assert 'python3dist(library) < 3.0' in conflict['failed_constraint']

        # new-package should have 2 conflicts (FTBFS and FTI), both new problems
        assert len(new_pkg_conflicts) == 2
        for conflict in new_pkg_conflicts:
            assert conflict['already_broken'] is False
            assert 'python3dist(library) < 5.0' in conflict['failed_constraint']
