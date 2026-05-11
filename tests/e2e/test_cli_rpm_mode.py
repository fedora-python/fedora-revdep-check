"""
End-to-end tests for CLI with RPM file mode.

Tests the command-line interface with --rpms and --rpm-dir options.
"""

import pytest
from unittest.mock import patch
from fedora_revdep_check import main


class TestCLIRPMMode:
    """Test CLI with --rpms option."""

    def test_cli_rpm_dir_not_found(self, tmp_path, capsys):
        """Test CLI with --rpm-dir when directory doesn't exist."""
        nonexistent = tmp_path / 'nonexistent'
        test_args = ['fedora-revdep-check', '--rpm-dir', str(nonexistent)]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert 'Directory not found' in captured.err

    def test_cli_rpm_dir_no_rpms(self, tmp_path, capsys):
        """Test CLI with --rpm-dir when directory has no RPM files."""
        test_args = ['fedora-revdep-check', '--rpm-dir', str(tmp_path)]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert 'No .rpm files found' in captured.err

    def test_cli_missing_arguments(self, capsys):
        """Test CLI with no arguments shows error."""
        test_args = ['fedora-revdep-check']

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()

        assert excinfo.value.code == 2  # argparse error
