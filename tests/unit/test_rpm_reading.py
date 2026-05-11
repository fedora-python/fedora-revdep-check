"""
Unit tests for RPM file reading functionality.

Uses real RPM files from tests/fixtures/rpms/ — no rpm module mocking.
Spec files for rebuilding the fixtures live in tests/fixtures/rpms/specs/.
"""

import pytest
from pathlib import Path
from fedora_revdep_check import FedoraRevDepChecker

RPM_DIR = Path(__file__).parent.parent / 'fixtures' / 'rpms'


class TestReadRPMProvides:
    """Test read_rpm_provides() against real RPM files."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    def test_read_single_rpm_file(self, checker):
        """Read a single RPM with Epoch: 1 and verify header fields."""
        rpm_file = str(RPM_DIR / 'revdeptest-epoch-9.1.0-1.noarch.rpm')

        result = checker.read_rpm_provides([rpm_file])

        assert result['srpm_name'] == 'revdeptest-epoch'
        assert 'revdeptest-epoch' in result['provides']
        assert 'python3dist(revdeptest-epoch)' in result['provides']
        assert len(result['rpm_info']) == 1

        info = result['rpm_info'][rpm_file]
        assert info['name'] == 'revdeptest-epoch'
        assert info['epoch'] == 1
        assert info['version'] == '9.1.0'
        assert info['release'] == '1'
        assert info['arch'] == 'noarch'
        assert info['evr'] == '1:9.1.0-1'

    def test_read_multiple_rpm_files(self, checker):
        """Read two binary RPMs from the same SRPM."""
        rpm_main = str(RPM_DIR / 'revdeptest-multi-1.0-1.noarch.rpm')
        rpm_sub = str(RPM_DIR / 'revdeptest-multi-sub-1.0-1.noarch.rpm')

        result = checker.read_rpm_provides([rpm_main, rpm_sub])

        assert result['srpm_name'] == 'revdeptest-multi'
        assert 'revdeptest-multi' in result['provides']
        assert 'python3dist(revdeptest-multi)' in result['provides']
        assert 'revdeptest-multi-sub' in result['provides']
        assert 'python3dist(revdeptest-multi-sub)' in result['provides']
        assert len(result['rpm_info']) == 2

    def test_skip_source_rpm(self, checker):
        """Source RPMs must be skipped even though their arch tag is 'noarch'.

        Real SRPMs on Fedora have Arch=noarch in their header, not Arch=src.
        The correct signal is RPMTAG_SOURCEPACKAGE=1, which is what the
        implementation checks.
        """
        srpm = str(RPM_DIR / 'revdeptest-foo-1.0-1.src.rpm')

        result = checker.read_rpm_provides([srpm])

        assert result['srpm_name'] == 'revdeptest-foo'
        assert len(result['provides']) == 0
        assert len(result['rpm_info']) == 0

    def test_skip_bundled_provides(self, checker):
        """Provides that start with 'bundled(' must be filtered out."""
        rpm_file = str(RPM_DIR / 'revdeptest-bundled-1.0-1.noarch.rpm')

        result = checker.read_rpm_provides([rpm_file])

        assert 'revdeptest-bundled' in result['provides']
        assert 'bundled(libfoo)' not in result['provides']
        assert 'bundled(libbar)' not in result['provides']

    def test_mixed_source_packages_error(self, checker):
        """Passing RPMs from two different SRPMs must raise ValueError."""
        rpm_foo = str(RPM_DIR / 'revdeptest-foo-1.0-1.noarch.rpm')
        rpm_bar = str(RPM_DIR / 'revdeptest-bar-1.0-1.noarch.rpm')

        with pytest.raises(ValueError, match="multiple source packages"):
            checker.read_rpm_provides([rpm_foo, rpm_bar])

    def test_file_not_found_error(self, checker):
        """A path that does not exist must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="RPM file not found"):
            checker.read_rpm_provides(['/nonexistent/file.rpm'])

    def test_rpm_without_epoch(self, checker):
        """Epoch defaults to 0 and evr is formatted without an epoch prefix."""
        rpm_file = str(RPM_DIR / 'revdeptest-foo-1.0-1.noarch.rpm')

        result = checker.read_rpm_provides([rpm_file])

        info = result['rpm_info'][rpm_file]
        assert info['epoch'] == 0
        assert info['evr'] == '1.0-1'
