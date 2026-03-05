"""
Unit tests for RPM file reading functionality.

Tests the read_rpm_provides() method which reads provides from actual RPM files.
"""

import pytest
from unittest.mock import Mock, mock_open, patch
from fedora_revdep_check import FedoraRevDepChecker


class MockRPMHeader:
    """Mock RPM header for testing."""

    def __init__(self, name, version, release, arch, epoch=None, sourcerpm=None,
                 provides_names=None, provides_versions=None, provides_flags=None):
        self.data = {
            1000: name.encode() if isinstance(name, str) else name,  # NAME
            1001: version.encode() if isinstance(version, str) else version,  # VERSION
            1002: release.encode() if isinstance(release, str) else release,  # RELEASE
            1022: arch.encode() if isinstance(arch, str) else arch,  # ARCH
            1003: epoch,  # EPOCH
            1044: sourcerpm.encode() if sourcerpm and isinstance(sourcerpm, str) else sourcerpm,  # SOURCERPM
            1047: provides_names,  # PROVIDENAME
            1113: provides_flags,  # PROVIDEFLAGS
            1048: provides_versions,  # PROVIDEVERSION
        }

    def __getitem__(self, key):
        return self.data.get(key)


class TestReadRPMProvides:
    """Test read_rpm_provides() method."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance with mocked DNF base."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    def test_read_single_rpm_file(self, checker):
        """Test reading a single RPM file."""
        mock_header = MockRPMHeader(
            name='python3-sphinx',
            version='9.1.0',
            release='1.fc45',
            arch='noarch',
            epoch=1,
            sourcerpm='python-sphinx-9.1.0-1.fc45.src.rpm',
            provides_names=[
                b'python3-sphinx',
                b'python3dist(sphinx)',
            ],
            provides_versions=[
                b'9.1.0-1.fc45',
                b'9.1.0',
            ],
            provides_flags=[
                8,  # RPMSENSE_EQUAL
                8,  # RPMSENSE_EQUAL
            ]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(return_value=mock_header)

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            result = checker.read_rpm_provides(['/tmp/test.rpm'])

            assert result['srpm_name'] == 'python-sphinx'
            assert 'python3-sphinx' in result['provides']
            assert 'python3dist(sphinx)' in result['provides']
            assert len(result['rpm_info']) == 1

            rpm_info = result['rpm_info']['/tmp/test.rpm']
            assert rpm_info['name'] == 'python3-sphinx'
            assert rpm_info['version'] == '9.1.0'
            assert rpm_info['release'] == '1.fc45'
            assert rpm_info['arch'] == 'noarch'
            assert rpm_info['epoch'] == 1

    def test_read_multiple_rpm_files(self, checker):
        """Test reading multiple RPM files from same SRPM."""
        mock_header1 = MockRPMHeader(
            name='python3-sphinx',
            version='9.1.0',
            release='1.fc45',
            arch='noarch',
            epoch=1,
            sourcerpm='python-sphinx-9.1.0-1.fc45.src.rpm',
            provides_names=[b'python3-sphinx', b'python3dist(sphinx)'],
            provides_versions=[b'9.1.0-1.fc45', b'9.1.0'],
            provides_flags=[8, 8]
        )

        mock_header2 = MockRPMHeader(
            name='python3-sphinx-latex',
            version='9.1.0',
            release='1.fc45',
            arch='noarch',
            epoch=1,
            sourcerpm='python-sphinx-9.1.0-1.fc45.src.rpm',
            provides_names=[b'python3-sphinx-latex'],
            provides_versions=[b'9.1.0-1.fc45'],
            provides_flags=[8]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(side_effect=[mock_header1, mock_header2])

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            result = checker.read_rpm_provides(['/tmp/test1.rpm', '/tmp/test2.rpm'])

            assert result['srpm_name'] == 'python-sphinx'
            assert 'python3-sphinx' in result['provides']
            assert 'python3dist(sphinx)' in result['provides']
            assert 'python3-sphinx-latex' in result['provides']
            assert len(result['rpm_info']) == 2

    def test_skip_source_rpm(self, checker):
        """Test that source RPMs are skipped for provides."""
        mock_header = MockRPMHeader(
            name='python-sphinx',
            version='9.1.0',
            release='1.fc45',
            arch='src',
            sourcerpm=None,
            provides_names=[b'python-sphinx'],
            provides_versions=[b'9.1.0-1.fc45'],
            provides_flags=[8]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(return_value=mock_header)

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            result = checker.read_rpm_provides(['/tmp/test.src.rpm'])

            assert result['srpm_name'] == 'python-sphinx'
            # Source RPM provides should be skipped
            assert len(result['provides']) == 0
            assert len(result['rpm_info']) == 0

    def test_skip_bundled_provides(self, checker):
        """Test that bundled provides are filtered out."""
        mock_header = MockRPMHeader(
            name='myapp',
            version='1.0.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='myapp-1.0.0-1.fc45.src.rpm',
            provides_names=[
                b'myapp',
                b'bundled(libfoo)',
                b'bundled(libbar)',
            ],
            provides_versions=[b'1.0.0', b'2.0', b'3.0'],
            provides_flags=[8, 8, 8]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(return_value=mock_header)

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            result = checker.read_rpm_provides(['/tmp/myapp.rpm'])

            assert 'myapp' in result['provides']
            assert 'bundled(libfoo)' not in result['provides']
            assert 'bundled(libbar)' not in result['provides']

    def test_mixed_source_packages_error(self, checker):
        """Test that mixing RPMs from different SRPMs raises error."""
        mock_header1 = MockRPMHeader(
            name='python3-sphinx',
            version='9.1.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='python-sphinx-9.1.0-1.fc45.src.rpm',
            provides_names=[b'python3-sphinx'],
            provides_versions=[b'9.1.0'],
            provides_flags=[8]
        )

        mock_header2 = MockRPMHeader(
            name='python3-requests',
            version='2.32.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='python-requests-2.32.0-1.fc45.src.rpm',
            provides_names=[b'python3-requests'],
            provides_versions=[b'2.32.0'],
            provides_flags=[8]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(side_effect=[mock_header1, mock_header2])

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            with pytest.raises(ValueError, match="multiple source packages"):
                checker.read_rpm_provides(['/tmp/test1.rpm', '/tmp/test2.rpm'])

    def test_file_not_found_error(self, checker):
        """Test error handling for missing RPM file."""
        with pytest.raises(FileNotFoundError, match="RPM file not found"):
            checker.read_rpm_provides(['/nonexistent/file.rpm'])

    def test_rpm_without_epoch(self, checker):
        """Test RPM file without epoch (epoch=None)."""
        mock_header = MockRPMHeader(
            name='mypackage',
            version='1.0.0',
            release='1.fc45',
            arch='noarch',
            epoch=None,
            sourcerpm='mypackage-1.0.0-1.fc45.src.rpm',
            provides_names=[b'mypackage'],
            provides_versions=[b'1.0.0'],
            provides_flags=[8]
        )

        mock_ts = Mock()
        mock_ts.hdrFromFdno = Mock(return_value=mock_header)

        with patch('rpm.TransactionSet', return_value=mock_ts), \
             patch('rpm._RPMVSF_NOSIGNATURES', 0), \
             patch('rpm._RPMVSF_NODIGESTS', 0), \
             patch('rpm.RPMTAG_NAME', 1000), \
             patch('rpm.RPMTAG_VERSION', 1001), \
             patch('rpm.RPMTAG_RELEASE', 1002), \
             patch('rpm.RPMTAG_ARCH', 1022), \
             patch('rpm.RPMTAG_EPOCH', 1003), \
             patch('rpm.RPMTAG_SOURCERPM', 1044), \
             patch('rpm.RPMTAG_PROVIDENAME', 1047), \
             patch('rpm.RPMTAG_PROVIDEFLAGS', 1113), \
             patch('rpm.RPMTAG_PROVIDEVERSION', 1048), \
             patch('rpm.RPMSENSE_EQUAL', 8), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()):

            result = checker.read_rpm_provides(['/tmp/test.rpm'])

            rpm_info = result['rpm_info']['/tmp/test.rpm']
            assert rpm_info['epoch'] == 0
            assert rpm_info['evr'] == '1.0.0-1.fc45'
