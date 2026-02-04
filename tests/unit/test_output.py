"""
Unit tests for output formatting.

Tests the print_results() method which formats and displays
conflict information in FTI/FTBFS format.
"""

import pytest
from fedora_revdep_check import FedoraRevDepChecker


class TestPrintResults:
    """Test print_results() output formatting."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    
    def test_print_results_no_conflicts(self, checker, capsys):
        """Test output when there are no conflicts (silent in non-verbose mode)."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '7.5.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': []
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Should be silent when no conflicts and not verbose
        assert captured.out == ''


    def test_print_results_no_conflicts_verbose(self, mock_dnf_base, capsys):
        """Test output when there are no conflicts in verbose mode."""
        checker = FedoraRevDepChecker(verbose=True, base=mock_dnf_base)
        results = {
            'srpm_name': 'pytest',
            'new_version': '7.5.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': []
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Should print message in verbose mode
        assert 'No conflicts detected' in captured.out
        assert 'pytest' in captured.out
        assert '7.5.0' in captured.out


    def test_print_results_fti_conflict(self, checker, capsys):
        """Test output for FTI (Fail To Install) conflict with binary package."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'python3-tox-4.0.0-1.fc40',
                    'rdep_source': 'tox',
                    'rdep_arch': 'noarch',  # Binary package -> FTI
                    'requirement': 'python3dist(pytest) >= 7.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0'
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check for FTI format
        assert 'These packages would FTI:' in captured.out
        assert 'python3-tox-4.0.0-1.fc40' in captured.out
        assert "python3dist(pytest) < 8.0" in captured.out


    def test_print_results_ftbfs_conflict(self, checker, capsys):
        """Test output for FTBFS (Fail To Build From Source) conflict with source package."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'tox-4.0.0-1.fc40',
                    'rdep_source': 'tox',
                    'rdep_arch': 'src',  # Source package -> FTBFS
                    'requirement': 'python3dist(pytest) >= 7.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0'
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check for FTBFS format
        assert 'These packages would FTBFS:' in captured.out
        assert 'tox' in captured.out  # Should use source name for FTBFS
        assert "python3dist(pytest) < 8.0" in captured.out


    def test_print_results_multiple_conflicts(self, checker, capsys):
        """Test output with multiple conflicts."""
        results = {
            'srpm_name': 'jupyterlab',
            'new_version': '4.7.0',
            'binary_packages': ['python3-jupyterlab-4.6.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'python3-jupyter-server-2.10.0-1.fc40',
                    'rdep_source': 'jupyter-server',
                    'rdep_arch': 'noarch',
                    'requirement': '(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 4.7)',
                    'provide_name': 'python3dist(jupyterlab)',
                    'new_version': '4.7.0',
                    'failed_constraint': 'python3dist(jupyterlab) < 4.7'
                },
                {
                    'rdep_package': 'python3-other-package-1.0.0-1.fc40',
                    'rdep_source': 'other-package',
                    'rdep_arch': 'noarch',
                    'requirement': 'python3dist(jupyterlab) < 4.7',
                    'provide_name': 'python3dist(jupyterlab)',
                    'new_version': '4.7.0',
                    'failed_constraint': 'python3dist(jupyterlab) < 4.7'
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check for header and content
        assert 'These packages would FTI:' in captured.out
        assert 'python3-jupyter-server-2.10.0-1.fc40' in captured.out
        assert 'python3-other-package-1.0.0-1.fc40' in captured.out
        assert 'python3dist(jupyterlab) < 4.7' in captured.out


    def test_print_results_error(self, checker, capsys):
        """Test output when there's an error."""
        results = {
            'error': 'No packages found for source package: nonexistent',
            'binary_packages': []
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        assert 'ERROR:' in captured.out
        assert 'No packages found' in captured.out
        assert 'nonexistent' in captured.out


    def test_print_results_one_line_per_conflict(self, checker, capsys):
        """Test that each conflict is printed with header and conflict line."""
        results = {
            'srpm_name': 'foo',
            'new_version': '2.0.0',
            'binary_packages': ['foo-1.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'bar-1.0.0-1.fc40',
                    'rdep_source': 'bar',
                    'rdep_arch': 'noarch',
                    'requirement': 'foo >= 1.0',
                    'provide_name': 'foo',
                    'new_version': '2.0.0',
                    'failed_constraint': 'foo < 2.0'
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Should have header plus conflict line
        assert 'These packages would FTI:' in captured.out
        assert 'bar-1.0.0-1.fc40' in captured.out
        assert 'foo < 2.0' in captured.out


    def test_print_results_both_ftbfs_and_fti(self, checker, capsys):
        """Test output when there are both FTBFS and FTI conflicts."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'tox-4.0.0-1.fc40',
                    'rdep_source': 'tox',
                    'rdep_arch': 'src',  # Source package -> FTBFS
                    'requirement': 'python3dist(pytest) >= 7.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0'
                },
                {
                    'rdep_package': 'python3-other-4.0.0-1.fc40',
                    'rdep_source': 'other',
                    'rdep_arch': 'noarch',  # Binary package -> FTI
                    'requirement': 'python3dist(pytest) < 8.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0'
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Should have both sections
        assert 'These packages would FTBFS:' in captured.out
        assert 'These packages would FTI:' in captured.out

        # Check FTBFS package
        assert 'tox' in captured.out

        # Check FTI package
        assert 'python3-other-4.0.0-1.fc40' in captured.out

        # Check constraint is in output
        assert 'python3dist(pytest) < 8.0' in captured.out


    def test_print_results_already_broken_ftbfs(self, checker, capsys):
        """Test output for already broken FTBFS packages."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'tox-4.0.0-1.fc40',
                    'rdep_source': 'tox',
                    'rdep_arch': 'src',
                    'requirement': 'python3dist(pytest) < 5.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 5.0',
                    'already_broken': True  # Current version also fails
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check for already broken FTBFS section
        assert 'These packages already FTBFS (not a new problem):' in captured.out
        assert 'tox' in captured.out
        assert 'python3dist(pytest) < 5.0' in captured.out
        # Should NOT appear in new FTBFS section
        assert 'These packages would FTBFS:' not in captured.out


    def test_print_results_already_broken_fti(self, checker, capsys):
        """Test output for already broken FTI packages."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'python3-tox-4.0.0-1.fc40',
                    'rdep_source': 'tox',
                    'rdep_arch': 'noarch',
                    'requirement': 'python3dist(pytest) < 5.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 5.0',
                    'already_broken': True  # Current version also fails
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check for already broken FTI section
        assert 'These packages already FTI (not a new problem):' in captured.out
        assert 'python3-tox-4.0.0-1.fc40' in captured.out
        assert 'python3dist(pytest) < 5.0' in captured.out
        # Should NOT appear in new FTI section
        assert 'These packages would FTI:' not in captured.out


    def test_print_results_mixed_new_and_already_broken(self, checker, capsys):
        """Test output with both new conflicts and already broken packages."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                # New FTBFS problem
                {
                    'rdep_package': 'newpkg-1.0.0-1.fc40',
                    'rdep_source': 'newpkg',
                    'rdep_arch': 'src',
                    'requirement': 'python3dist(pytest) < 8.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0',
                    'already_broken': False  # New problem
                },
                # Already broken FTBFS
                {
                    'rdep_package': 'oldpkg-1.0.0-1.fc40',
                    'rdep_source': 'oldpkg',
                    'rdep_arch': 'src',
                    'requirement': 'python3dist(pytest) < 5.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 5.0',
                    'already_broken': True
                },
                # New FTI problem
                {
                    'rdep_package': 'python3-newpkg2-1.0.0-1.fc40',
                    'rdep_source': 'newpkg2',
                    'rdep_arch': 'noarch',
                    'requirement': 'python3dist(pytest) < 8.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 8.0',
                    'already_broken': False
                },
                # Already broken FTI
                {
                    'rdep_package': 'python3-oldpkg2-1.0.0-1.fc40',
                    'rdep_source': 'oldpkg2',
                    'rdep_arch': 'noarch',
                    'requirement': 'python3dist(pytest) < 5.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 5.0',
                    'already_broken': True
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Check all four sections appear
        assert 'These packages would FTBFS:' in captured.out
        assert 'These packages would FTI:' in captured.out
        assert 'These packages already FTBFS (not a new problem):' in captured.out
        assert 'These packages already FTI (not a new problem):' in captured.out

        # Check new problems
        assert 'newpkg' in captured.out
        assert 'python3-newpkg2-1.0.0-1.fc40' in captured.out

        # Check already broken
        assert 'oldpkg' in captured.out
        assert 'python3-oldpkg2-1.0.0-1.fc40' in captured.out

        # Check constraints
        assert 'python3dist(pytest) < 8.0' in captured.out
        assert 'python3dist(pytest) < 5.0' in captured.out


    def test_print_results_only_already_broken(self, checker, capsys):
        """Test output with only already broken packages (no new problems)."""
        results = {
            'srpm_name': 'pytest',
            'new_version': '8.0.0',
            'binary_packages': ['python3-pytest-7.0.0-1.fc40'],
            'conflicts': [
                {
                    'rdep_package': 'oldpkg-1.0.0-1.fc40',
                    'rdep_source': 'oldpkg',
                    'rdep_arch': 'src',
                    'requirement': 'python3dist(pytest) < 5.0',
                    'provide_name': 'python3dist(pytest)',
                    'new_version': '8.0.0',
                    'failed_constraint': 'python3dist(pytest) < 5.0',
                    'already_broken': True
                }
            ]
        }

        checker.print_results(results)
        captured = capsys.readouterr()

        # Should only show already broken section
        assert 'These packages already FTBFS (not a new problem):' in captured.out
        assert 'oldpkg' in captured.out

        # Should NOT show new problem sections
        assert 'These packages would FTBFS:' not in captured.out
        assert 'These packages would FTI:' not in captured.out
