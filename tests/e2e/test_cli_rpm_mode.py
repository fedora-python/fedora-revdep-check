"""
End-to-end tests for CLI with RPM file mode.

Tests the command-line interface with --rpms and --rpm-dir options.
"""

from unittest.mock import patch
from fedora_revdep_check import main


class TestCLIRPMMode:
    """Test CLI with --rpms option."""

    def test_cli_rpm_dir_not_found(self, capsys):
        """Test CLI with --rpm-dir when directory doesn't exist."""
        test_args = ['fedora-revdep-check', '--rpm-dir', '/nonexistent']

        with patch('sys.argv', test_args), \
             patch('os.path.isdir', return_value=False):

            exit_code = 0
            try:
                main()
            except SystemExit as e:
                exit_code = e.code

            assert exit_code == 1
            captured = capsys.readouterr()
            assert 'Directory not found' in captured.err

    def test_cli_rpm_dir_no_rpms(self, capsys):
        """Test CLI with --rpm-dir when directory has no RPM files."""
        test_args = ['fedora-revdep-check', '--rpm-dir', '/tmp/empty']

        with patch('sys.argv', test_args), \
             patch('os.path.isdir', return_value=True), \
             patch('glob.glob', return_value=[]):

            exit_code = 0
            try:
                main()
            except SystemExit as e:
                exit_code = e.code

            assert exit_code == 1
            captured = capsys.readouterr()
            assert 'No .rpm files found' in captured.err

    def test_cli_missing_arguments(self, capsys):
        """Test CLI with no arguments shows error."""
        test_args = ['fedora-revdep-check']

        with patch('sys.argv', test_args):
            exit_code = 0
            try:
                main()
            except SystemExit as e:
                exit_code = e.code

            assert exit_code == 2  # argparse error
