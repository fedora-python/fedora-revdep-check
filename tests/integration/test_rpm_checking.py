"""
Integration tests for check_rpm_files() functionality.

Tests the complete workflow of checking RPM files for reverse dependency conflicts.
"""

from unittest.mock import Mock, mock_open, patch
from fedora_revdep_check import FedoraRevDepChecker
from tests.fixtures.mock_packages import MockPackage, MockBase


class MockRPMHeader:
    """Mock RPM header for testing."""

    def __init__(self, name, version, release, arch, epoch=None, sourcerpm=None,
                 provides_names=None, provides_versions=None, provides_flags=None):
        self.data = {
            1000: name.encode() if isinstance(name, str) else name,
            1001: version.encode() if isinstance(version, str) else version,
            1002: release.encode() if isinstance(release, str) else release,
            1022: arch.encode() if isinstance(arch, str) else arch,
            1003: epoch,
            1044: sourcerpm.encode() if sourcerpm and isinstance(sourcerpm, str) else sourcerpm,
            1047: provides_names,
            1113: provides_flags,
            1048: provides_versions,
        }

    def __getitem__(self, key):
        return self.data.get(key)


class TestCheckRPMFiles:
    """Test check_rpm_files() integration."""

    def test_check_rpm_files_no_conflicts(self):
        """Test checking RPM files that don't cause conflicts."""
        # Create a mock base with packages that depend on pytest >= 7.0
        packages = [
            MockPackage(
                name='python3-pytest',
                version='7.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='pytest',
                provides=[
                    'python3-pytest',
                    'python3dist(pytest) = 7.0.0',
                ]
            ),
            MockPackage(
                name='python3-tox',
                version='4.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='tox',
                requires=[
                    'python3dist(pytest) >= 6.0',
                ]
            ),
        ]
        base = MockBase(packages=packages)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        # Mock RPM for pytest 7.1.0
        mock_header = MockRPMHeader(
            name='python3-pytest',
            version='7.1.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='pytest-7.1.0-1.fc45.src.rpm',
            provides_names=[
                b'python3-pytest',
                b'python3dist(pytest)',
            ],
            provides_versions=[
                b'7.1.0-1.fc45',
                b'7.1.0',
            ],
            provides_flags=[8, 8]
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

            result = checker.check_rpm_files(['/tmp/pytest.rpm'])

            assert result['srpm_name'] == 'pytest'
            assert result['new_version'] == '7.1.0-1.fc45'
            assert len(result['conflicts']) == 0

    def test_check_rpm_files_with_conflicts(self):
        """Test checking RPM files that cause conflicts."""
        # Create a mock base with packages that depend on jupyterlab < 4.7
        packages = [
            MockPackage(
                name='python3-jupyterlab',
                version='4.6.0',
                release='1.fc45',
                arch='noarch',
                source_name='jupyterlab',
                provides=[
                    'python3-jupyterlab',
                    'python3dist(jupyterlab) = 4.6.0',
                ]
            ),
            MockPackage(
                name='python3-jupyter-server',
                version='2.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='jupyter-server',
                requires=[
                    'python3dist(jupyterlab) < 4.7',
                ]
            ),
        ]
        base = MockBase(packages=packages)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        # Mock RPM for jupyterlab 4.7.0
        mock_header = MockRPMHeader(
            name='python3-jupyterlab',
            version='4.7.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='jupyterlab-4.7.0-1.fc45.src.rpm',
            provides_names=[
                b'python3-jupyterlab',
                b'python3dist(jupyterlab)',
            ],
            provides_versions=[
                b'4.7.0-1.fc45',
                b'4.7.0',
            ],
            provides_flags=[8, 8]
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

            result = checker.check_rpm_files(['/tmp/jupyterlab.rpm'])

            assert result['srpm_name'] == 'jupyterlab'
            assert len(result['conflicts']) == 1
            conflict = result['conflicts'][0]
            assert conflict['rdep_source'] == 'jupyter-server'
            assert conflict['provide_name'] == 'python3dist(jupyterlab)'
            assert 'python3dist(jupyterlab) < 4.7' in conflict['failed_constraint']

    def test_check_rpm_files_with_epoch(self):
        """Test checking RPM files with epochs."""
        # Create a mock base with packages requiring sphinx >= 1:8.0.0
        packages = [
            MockPackage(
                name='python3-sphinx',
                version='8.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='python-sphinx',  # Must match SOURCERPM
                epoch='1',
                provides=[
                    'python3-sphinx',
                    'python3-sphinx = 1:8.0.0-1.fc45',
                    'python3dist(sphinx) = 8.0.0',
                ]
            ),
            MockPackage(
                name='python3-docs',
                version='1.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='python-docs',
                requires=[
                    'python3-sphinx >= 1:8.0.0',
                ]
            ),
        ]
        base = MockBase(packages=packages)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        # Mock RPM for sphinx 1:9.1.0
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
            provides_flags=[8, 8]
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

            result = checker.check_rpm_files(['/tmp/sphinx.rpm'])

            assert result['srpm_name'] == 'python-sphinx'
            # Should have no conflicts (1:9.1.0 >= 1:8.0.0)
            assert len(result['conflicts']) == 0

    def test_check_rpm_files_skips_same_srpm(self):
        """Test that packages from same SRPM are skipped."""
        # Create a mock base where packages from the same SRPM depend on each other
        packages = [
            MockPackage(
                name='micropipenv',
                version='1.10.0',
                release='1.fc45',
                arch='noarch',
                source_name='micropipenv',
                provides=[
                    'micropipenv',
                    'micropipenv = 1.10.0-1.fc45',
                ]
            ),
            MockPackage(
                name='micropipenv+toml',
                version='1.10.0',
                release='1.fc45',
                arch='noarch',
                source_name='micropipenv',
                requires=[
                    'micropipenv = 1.10.0',
                ]
            ),
        ]
        base = MockBase(packages=packages)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        # Mock RPM for micropipenv 1.11.0
        mock_header = MockRPMHeader(
            name='micropipenv',
            version='1.11.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='micropipenv-1.11.0-1.fc45.src.rpm',
            provides_names=[
                b'micropipenv',
            ],
            provides_versions=[
                b'1.11.0-1.fc45',
            ],
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

            result = checker.check_rpm_files(['/tmp/micropipenv.rpm'])

            # micropipenv+toml should be skipped (same SRPM)
            assert len(result['conflicts']) == 0

    def test_check_rpm_files_already_broken(self):
        """Test detection of already-broken packages."""
        # Create a mock base where a package already fails with current version
        packages = [
            MockPackage(
                name='library',
                version='4.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='library',
                provides=[
                    'library',
                    'python3dist(library) = 4.0.0',
                ]
            ),
            MockPackage(
                name='python3-old-package',
                version='1.0.0',
                release='1.fc45',
                arch='noarch',
                source_name='old-package',
                requires=[
                    'python3dist(library) < 3.0',  # Already broken with 4.0.0
                ]
            ),
        ]
        base = MockBase(packages=packages)
        checker = FedoraRevDepChecker(verbose=False, base=base)

        # Mock RPM for library 5.0.0
        mock_header = MockRPMHeader(
            name='library',
            version='5.0.0',
            release='1.fc45',
            arch='noarch',
            sourcerpm='library-5.0.0-1.fc45.src.rpm',
            provides_names=[
                b'library',
                b'python3dist(library)',
            ],
            provides_versions=[
                b'5.0.0-1.fc45',
                b'5.0.0',
            ],
            provides_flags=[8, 8]
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

            result = checker.check_rpm_files(['/tmp/library.rpm'])

            assert len(result['conflicts']) == 1
            conflict = result['conflicts'][0]
            assert conflict['already_broken'] is True
            assert 'python3dist(library) < 3.0' in conflict['failed_constraint']
