"""
Integration tests for check_rpm_files() functionality.

Uses real RPM files from tests/fixtures/rpms/ for the RPM-reading layer.
The DNF layer (repository queries, reverse dependency lookup) is still mocked
via MockBase/MockPackage — that part has its own tests elsewhere.

Spec files for rebuilding the fixtures live in tests/fixtures/rpms/specs/.
"""

from pathlib import Path

from fedora_revdep_check import FedoraRevDepChecker
from tests.fixtures.mock_packages import MockPackage, MockBase

RPM_DIR = Path(__file__).parent.parent / 'fixtures' / 'rpms'


class TestCheckRPMFiles:
    """Test check_rpm_files() end-to-end with real RPM files."""

    def test_check_rpm_files_no_conflicts(self):
        """Updating revdeptest-foo to 1.0 satisfies all existing requirements."""
        packages = [
            MockPackage(
                name='revdeptest-foo',
                version='0.9',
                release='1',
                arch='noarch',
                source_name='revdeptest-foo',
                provides=[
                    'revdeptest-foo',
                    'python3dist(revdeptest-foo) = 0.9',
                ]
            ),
            MockPackage(
                name='consumer',
                version='1.0',
                release='1',
                arch='noarch',
                source_name='consumer',
                requires=[
                    'python3dist(revdeptest-foo) >= 0.5',
                ]
            ),
        ]
        checker = FedoraRevDepChecker(verbose=False, base=MockBase(packages=packages))

        result = checker.check_rpm_files([str(RPM_DIR / 'revdeptest-foo-1.0-1.noarch.rpm')])

        assert result['srpm_name'] == 'revdeptest-foo'
        assert len(result['conflicts']) == 0

    def test_check_rpm_files_with_conflicts(self):
        """Updating revdeptest-foo to 1.0 breaks a package requiring < 1.0."""
        packages = [
            MockPackage(
                name='revdeptest-foo',
                version='0.9',
                release='1',
                arch='noarch',
                source_name='revdeptest-foo',
                provides=[
                    'revdeptest-foo',
                    'python3dist(revdeptest-foo) = 0.9',
                ]
            ),
            MockPackage(
                name='old-consumer',
                version='1.0',
                release='1',
                arch='noarch',
                source_name='old-consumer',
                requires=[
                    'python3dist(revdeptest-foo) < 1.0',
                ]
            ),
        ]
        checker = FedoraRevDepChecker(verbose=False, base=MockBase(packages=packages))

        result = checker.check_rpm_files([str(RPM_DIR / 'revdeptest-foo-1.0-1.noarch.rpm')])

        assert result['srpm_name'] == 'revdeptest-foo'
        assert len(result['conflicts']) == 1
        conflict = result['conflicts'][0]
        assert conflict['rdep_source'] == 'old-consumer'
        assert conflict['provide_name'] == 'python3dist(revdeptest-foo)'
        assert 'python3dist(revdeptest-foo) < 1.0' in conflict['failed_constraint']

    def test_check_rpm_files_with_epoch(self):
        """Updating revdeptest-epoch (Epoch:1) to 9.1.0 satisfies >= 1:8.0.0."""
        packages = [
            MockPackage(
                name='revdeptest-epoch',
                version='8.0.0',
                release='1',
                arch='noarch',
                source_name='revdeptest-epoch',
                epoch='1',
                provides=[
                    'revdeptest-epoch',
                    'revdeptest-epoch = 1:8.0.0-1',
                    'python3dist(revdeptest-epoch) = 8.0.0',
                ]
            ),
            MockPackage(
                name='consumer',
                version='1.0',
                release='1',
                arch='noarch',
                source_name='consumer',
                requires=[
                    'revdeptest-epoch >= 1:8.0.0',
                ]
            ),
        ]
        checker = FedoraRevDepChecker(verbose=False, base=MockBase(packages=packages))

        result = checker.check_rpm_files([str(RPM_DIR / 'revdeptest-epoch-9.1.0-1.noarch.rpm')])

        assert result['srpm_name'] == 'revdeptest-epoch'
        assert len(result['conflicts']) == 0

    def test_check_rpm_files_skips_same_srpm(self):
        """Packages from the same SRPM are not flagged as conflicts."""
        packages = [
            MockPackage(
                name='revdeptest-multi',
                version='0.9',
                release='1',
                arch='noarch',
                source_name='revdeptest-multi',
                provides=[
                    'revdeptest-multi',
                    'python3dist(revdeptest-multi) = 0.9',
                ]
            ),
            MockPackage(
                name='revdeptest-multi-sub',
                version='0.9',
                release='1',
                arch='noarch',
                source_name='revdeptest-multi',
                requires=[
                    'revdeptest-multi = 0.9',
                ]
            ),
        ]
        checker = FedoraRevDepChecker(verbose=False, base=MockBase(packages=packages))

        result = checker.check_rpm_files([str(RPM_DIR / 'revdeptest-multi-1.0-1.noarch.rpm')])

        assert len(result['conflicts']) == 0

    def test_check_rpm_files_already_broken(self):
        """A conflict that exists before the update is marked already_broken."""
        packages = [
            MockPackage(
                name='revdeptest-foo',
                version='0.9',
                release='1',
                arch='noarch',
                source_name='revdeptest-foo',
                provides=[
                    'revdeptest-foo',
                    'python3dist(revdeptest-foo) = 0.9',
                ]
            ),
            MockPackage(
                name='old-consumer',
                version='1.0',
                release='1',
                arch='noarch',
                source_name='old-consumer',
                requires=[
                    'python3dist(revdeptest-foo) < 0.5',  # already broken with 0.9
                ]
            ),
        ]
        checker = FedoraRevDepChecker(verbose=False, base=MockBase(packages=packages))

        result = checker.check_rpm_files([str(RPM_DIR / 'revdeptest-foo-1.0-1.noarch.rpm')])

        assert len(result['conflicts']) == 1
        conflict = result['conflicts'][0]
        assert conflict['already_broken'] is True
        assert 'python3dist(revdeptest-foo) < 0.5' in conflict['failed_constraint']
