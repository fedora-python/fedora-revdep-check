"""
Unit tests for requirement matching operations.

Tests the _requirement_matches_provide() and _check_requirement_conflict()
methods which handle parsing and matching of RPM dependency strings.
"""

import pytest
from fedora_revdep_check import FedoraRevDepChecker
from tests.fixtures.mock_packages import MockPackage


class TestRequirementMatchesProvide:
    """Test requirement matching logic to prevent false positives."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance with mocked DNF base."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    
    @pytest.mark.parametrize("req_str,prov_name,expected", [
        # Exact matches
        ("pytest", "pytest", True),
        ("python3dist(pytest)", "python3dist(pytest)", True),
        ("foo", "foo", True),

        # With version constraints
        ("pytest >= 7.0", "pytest", True),
        ("pytest < 8.0", "pytest", True),
        ("python3dist(pytest) >= 7.0.0", "python3dist(pytest)", True),
        ("foo > 1.0", "foo", True),

        # False positives that should NOT match
        ("pytest-xdist", "pytest", False),
        ("python3dist(pytest-xdist)", "python3dist(pytest)", False),
        ("pytest-xdist >= 3.0", "pytest", False),
        ("foo-bar", "foo", False),
        ("foobar", "foo", False),

        # Parentheses in provide names
        ("python3dist(pytest)", "python3dist(pytest)", True),
        ("python3dist(pytest) >= 7", "python3dist(pytest)", True),
        ("python3dist(pytest-xdist)", "python3dist(pytest)", False),

        # Edge cases with operators
        ("pytest>= 7.0", "pytest", True),
        ("pytest>7.0", "pytest", True),
        ("pytest<8.0", "pytest", True),
        ("pytest==7.0", "pytest", True),
        ("pytest!=6.0", "pytest", True),
    ])
    def test_requirement_matches_provide_simple(self, checker, req_str, prov_name, expected):
        """Test simple requirement matching."""
        result = checker._requirement_matches_provide(req_str, prov_name)
        assert result == expected, f"'{req_str}' matching '{prov_name}' should be {expected}"

    
    @pytest.mark.parametrize("req_str,prov_name,expected", [
        # Rich dependency with "with" operator
        ("(pytest >= 4 with pytest < 5)", "pytest", True),
        ("(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 4.7)", "python3dist(jupyterlab)", True),
        ("(foo >= 2.0 with foo < 3.0)", "foo", True),

        # Rich dependency with "or"
        ("(pytest or pytest-xdist)", "pytest", True),
        ("(pytest or pytest-xdist)", "pytest-xdist", True),
        ("(pytest or nose)", "pytest", True),
        ("(pytest or nose)", "nose", True),

        # Rich dependency with "and"
        ("(pytest and python3)", "pytest", True),
        ("(pytest and python3)", "python3", True),

        # Rich dependency should not match unrelated provides
        ("(pytest >= 4 with pytest < 5)", "pytest-xdist", False),
        ("(foo >= 2.0 with foo < 3.0)", "bar", False),

        # Rich dependency with "if" and "unless"
        ("(pytest if python3)", "pytest", True),
        ("(pytest if python3)", "python3", True),
        ("(pytest unless python2)", "pytest", True),
    ])
    def test_requirement_matches_provide_rich_deps(self, checker, req_str, prov_name, expected):
        """Test rich dependency matching."""
        result = checker._requirement_matches_provide(req_str, prov_name)
        assert result == expected, f"'{req_str}' matching '{prov_name}' should be {expected}"


class TestCheckRequirementConflict:
    """Test requirement conflict detection logic."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance with mocked DNF base."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    @pytest.fixture
    def mock_rdep_pkg(self):
        """Create a mock reverse dependency package."""
        return MockPackage(
            name='test-rdep',
            version='1.0.0',
            release='1.fc40',
            arch='noarch',
            source_name='test-rdep',
        )

    
    def test_check_requirement_conflict_greater_than_fails(self, checker, mock_rdep_pkg):
        """Test conflict when new version is less than requirement."""
        conflict = checker._check_requirement_conflict(
            req_str="pytest >= 8.0",
            prov_name="pytest",
            new_version="7.5.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is not None
        assert conflict['rdep_package'] == 'test-rdep-1.0.0-1.fc40'
        assert conflict['rdep_source'] == 'test-rdep'
        assert conflict['rdep_arch'] == 'noarch'
        assert conflict['failed_constraint'] == 'pytest >= 8.0'
        assert conflict['new_version'] == '7.5.0'

    
    def test_check_requirement_conflict_greater_than_passes(self, checker, mock_rdep_pkg):
        """Test no conflict when new version satisfies >= requirement."""
        conflict = checker._check_requirement_conflict(
            req_str="pytest >= 7.0",
            prov_name="pytest",
            new_version="7.5.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is None

    
    def test_check_requirement_conflict_less_than_fails(self, checker, mock_rdep_pkg):
        """Test conflict when new version exceeds upper bound."""
        conflict = checker._check_requirement_conflict(
            req_str="python3dist(jupyterlab) < 4.7",
            prov_name="python3dist(jupyterlab)",
            new_version="4.7.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is not None
        assert conflict['failed_constraint'] == 'python3dist(jupyterlab) < 4.7'

    
    def test_check_requirement_conflict_less_than_passes(self, checker, mock_rdep_pkg):
        """Test no conflict when new version is below upper bound."""
        conflict = checker._check_requirement_conflict(
            req_str="python3dist(jupyterlab) < 5.0",
            prov_name="python3dist(jupyterlab)",
            new_version="4.7.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is None

    
    def test_check_requirement_conflict_rich_dep_with_clause_fails(self, checker, mock_rdep_pkg):
        """Test conflict with rich dependency (with clause)."""
        conflict = checker._check_requirement_conflict(
            req_str="(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 4.7)",
            prov_name="python3dist(jupyterlab)",
            new_version="4.7.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is not None
        assert conflict['failed_constraint'] == 'python3dist(jupyterlab) < 4.7'

    
    def test_check_requirement_conflict_rich_dep_with_clause_passes(self, checker, mock_rdep_pkg):
        """Test no conflict with rich dependency when version is in range."""
        conflict = checker._check_requirement_conflict(
            req_str="(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 5)",
            prov_name="python3dist(jupyterlab)",
            new_version="4.7.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is None

    
    def test_check_requirement_conflict_no_version_constraint(self, checker, mock_rdep_pkg):
        """Test no conflict when requirement has no version constraint."""
        conflict = checker._check_requirement_conflict(
            req_str="pytest",
            prov_name="pytest",
            new_version="99.99.99",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is None

    
    def test_check_requirement_conflict_ftbfs_detection(self, checker):
        """Test that source packages are correctly identified for FTBFS."""
        src_pkg = MockPackage(
            name='test-srpm',
            version='1.0.0',
            release='1.fc40',
            arch='src',  # Source package
            source_name='test-srpm',
        )

        conflict = checker._check_requirement_conflict(
            req_str="pytest >= 8.0",
            prov_name="pytest",
            new_version="7.5.0",
            rdep_pkg=src_pkg,
            prov_info_list=[]
        )

        assert conflict is not None
        assert conflict['rdep_arch'] == 'src'
        # This should trigger FTBFS in output formatting

    
    def test_check_requirement_conflict_fti_detection(self, checker, mock_rdep_pkg):
        """Test that binary packages are correctly identified for FTI."""
        conflict = checker._check_requirement_conflict(
            req_str="pytest >= 8.0",
            prov_name="pytest",
            new_version="7.5.0",
            rdep_pkg=mock_rdep_pkg,
            prov_info_list=[]
        )

        assert conflict is not None
        assert conflict['rdep_arch'] == 'noarch'
        # This should trigger FTI in output formatting
