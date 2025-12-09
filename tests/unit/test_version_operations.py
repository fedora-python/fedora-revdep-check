"""
Unit tests for version comparison operations.

Tests the _version_satisfies() method which uses RPM version comparison
logic to determine if a version meets a requirement.
"""

import pytest
from fedora_revdep_check import FedoraRevDepChecker


class TestVersionSatisfies:
    """Test RPM version comparison logic."""

    @pytest.fixture
    def checker(self, mock_dnf_base):
        """Create checker instance with mocked DNF base."""
        return FedoraRevDepChecker(verbose=False, base=mock_dnf_base)

    
    @pytest.mark.parametrize("version,op,required,expected", [
        # Greater than tests
        ("4.7.0", ">", "4.6.0", True),
        ("4.6.0", ">", "4.7.0", False),
        ("4.7.0", ">", "4.7.0", False),
        ("5.0.0", ">", "4.7.0", True),

        # Greater than or equal tests
        ("4.7.0", ">=", "4.6.0", True),
        ("4.7.0", ">=", "4.7.0", True),
        ("4.6.0", ">=", "4.7.0", False),
        ("5.0.0", ">=", "4.7.0", True),

        # Less than tests
        ("4.6.0", "<", "4.7.0", True),
        ("4.7.0", "<", "4.6.0", False),
        ("4.7.0", "<", "4.7.0", False),
        ("4.7.0", "<", "5.0.0", True),

        # Less than or equal tests
        ("4.6.0", "<=", "4.7.0", True),
        ("4.7.0", "<=", "4.7.0", True),
        ("4.7.0", "<=", "4.6.0", False),
        ("4.7.0", "<=", "5.0.0", True),

        # Equality tests
        ("4.7.0", "=", "4.7.0", True),
        ("4.7.0", "==", "4.7.0", True),
        ("4.7.0", "=", "4.6.0", False),
        ("4.7.0", "==", "4.8.0", False),

        # Inequality tests
        ("4.7.0", "!=", "4.6.0", True),
        ("4.7.0", "!=", "4.7.0", False),
        ("4.7.0", "!=", "4.8.0", True),
    ])
    def test_version_satisfies_basic_operators(self, checker, version, op, required, expected):
        """Test version comparison with basic operators."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"

    
    @pytest.mark.parametrize("version,op,required,expected", [
        # Tilde (pre-release) tests - tilde makes version lower
        ("4.7.0~rc1", "<", "4.7.0", True),
        ("4.7.0", ">", "4.7.0~rc1", True),
        ("4.7.0~rc2", ">", "4.7.0~rc1", True),
        ("4.7.0~alpha", "<", "4.7.0~beta", True),
        ("4.7.0~rc1", ">=", "4.7.0~rc1", True),
        ("4.7.0~rc1", "!=", "4.7.0", True),

        # Test that tilde orders correctly
        ("4.7.0~rc1", "<", "4.7.0~rc2", True),
        ("4.7.0~rc10", ">", "4.7.0~rc2", True),  # Numeric sorting
    ])
    def test_version_satisfies_tilde(self, checker, version, op, required, expected):
        """Test version comparison with tilde (pre-release) versions."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"

    
    @pytest.mark.parametrize("version,op,required,expected", [
        # Epoch tests - epoch overrides version
        ("1:2.0.0", ">", "3.0.0", True),  # Epoch 1 > epoch 0
        ("2.0.0", "<", "1:1.0.0", True),  # Epoch 0 < epoch 1
        ("1:2.0.0", "=", "1:2.0.0", True),
        ("1:2.0.0", "!=", "2:2.0.0", True),
        ("2:1.0.0", ">", "1:9.9.9", True),  # Higher epoch wins

        # Epoch with same version
        ("1:4.7.0", ">", "4.7.0", True),
        ("4.7.0", "<", "1:4.7.0", True),
    ])
    def test_version_satisfies_epoch(self, checker, version, op, required, expected):
        """Test version comparison with epoch versions."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"

    
    @pytest.mark.parametrize("version,op,required,expected", [
        # Release tests
        ("2.3.4-2", ">", "2.3.4-1", True),
        ("2.3.4-1", "<", "2.3.4-2", True),
        ("2.3.4-1", ">=", "2.3.4-1", True),
        ("2.3.4-1", "=", "2.3.4-1", True),
        ("2.3.4-10", ">", "2.3.4-2", True),  # Numeric sorting

        # Version with and without release - RPM treats missing release as -0
        ("2.3.4-1", ">", "2.3.4-0", True),  # Explicit comparison
        ("2.3.5", ">", "2.3.4-10", True),  # Version comparison first
    ])
    def test_version_satisfies_release(self, checker, version, op, required, expected):
        """Test version comparison with release numbers."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"

    
    @pytest.mark.parametrize("version,op,required,expected", [
        # Complex combinations
        ("1:2.3.4-5", ">", "0:2.3.4-10", True),  # Epoch wins
        ("1:2.3.4-1", ">", "1:2.3.3-100", True),  # Version wins with same epoch
        ("1:2.3.4-5", "=", "1:2.3.4-5", True),  # Exact match

        # Pre-release with epoch and release
        ("1:4.7.0~rc1-1", "<", "1:4.7.0-1", True),
        ("1:4.7.0~rc1-2", ">", "1:4.7.0~rc1-1", True),
    ])
    def test_version_satisfies_complex(self, checker, version, op, required, expected):
        """Test version comparison with complex EVR combinations."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"

    
    def test_version_satisfies_invalid_operator(self, checker):
        """Test handling of invalid operators."""
        result = checker._version_satisfies("4.7.0", "~>", "4.6.0")
        assert result is False


    @pytest.mark.parametrize("version,op,required,expected", [
        # Double tilde (very pre-release)
        ("4.7.0~~alpha", "<", "4.7.0~beta", True),
        ("4.7.0~~", "<", "4.7.0~", True),

        # Caret tests (post-release) - not as common but should work
        ("4.7.0^post1", ">", "4.7.0", True),

        # Real-world version comparisons
        ("3.11.0", ">", "3.10.9", True),
        ("3.11.0", "<", "3.11.1", True),

        # RPM-style pre-releases (use tilde, not Python's 'a' or 'rc')
        ("3.11.0~a1", "<", "3.11.0", True),
        ("3.11.0~rc1", "<", "3.11.0", True),
    ])
    def test_version_satisfies_edge_cases(self, checker, version, op, required, expected):
        """Test version comparison edge cases."""
        result = checker._version_satisfies(version, op, required)
        assert result == expected, f"{version} {op} {required} should be {expected}"
