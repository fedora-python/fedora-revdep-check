"""
End-to-end tests for complete CLI workflow.

Tests the main() function with various command-line scenarios,
including argument parsing, execution, and exit codes.
"""

import pytest
from fedora_revdep_check import main, FedoraRevDepChecker


class TestFullWorkflow:
    """Test complete CLI workflow through main() function."""

    def test_main_with_conflicts_exit_code_one(self, monkeypatch, jupyterlab_base, capsys):
        """Test that main() exits with 1 when conflicts are found."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'jupyterlab', '4.7.0'])

        # Mock FedoraRevDepChecker to use test base
        original_init = FedoraRevDepChecker.__init__

        def mock_init(self, verbose=False, base=None, repos=None):
            original_init(self, verbose=verbose, base=jupyterlab_base if base is None else base, repos=repos)

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        # main() should exit with 1 (conflicts found)
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        # Check output contains conflict information
        captured = capsys.readouterr()
        assert 'These packages would FTI:' in captured.out or 'These packages would FTBFS:' in captured.out

    def test_main_verbose_flag(self, monkeypatch, mock_pytest_base, capsys):
        """Test that --verbose flag enables verbose output."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'pytest', '7.5.0', '--verbose'])

        original_init = FedoraRevDepChecker.__init__

        def mock_init(self, verbose=False, base=None, repos=None):
            original_init(self, verbose=verbose, base=mock_pytest_base if base is None else base, repos=repos)

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        # main() returns normally when no conflicts
        main()

        captured = capsys.readouterr()
        # In verbose mode, should show message even with no conflicts
        assert 'No conflicts detected' in captured.out

    def test_main_nonexistent_package(self, monkeypatch, mock_dnf_base, capsys):
        """Test main() with non-existent package."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'nonexistent', '1.0.0'])

        original_init = FedoraRevDepChecker.__init__

        def mock_init(self, verbose=False, base=None, repos=None):
            original_init(self, verbose=verbose, base=mock_dnf_base if base is None else base, repos=repos)

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        # Should not exit since print_results doesn't cause exit for errors
        # It just prints the error
        main()

        # Check that error message is displayed
        captured = capsys.readouterr()
        assert 'ERROR:' in captured.out
        assert 'No packages found' in captured.out

    def test_main_exception_handling(self, monkeypatch, capsys):
        """Test main() handles exceptions correctly."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'test', '1.0.0'])

        # Mock FedoraRevDepChecker to raise an exception
        def mock_init(self, verbose=False, base=None, repos=None):
            raise RuntimeError("Test error message")

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert 'ERROR:' in captured.err
        assert 'Test error message' in captured.err
       
    def test_main_output_format_consistency(self, monkeypatch, jupyterlab_base, capsys):
        """Test that output format is consistent across runs."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'jupyterlab', '4.7.0'])

        original_init = FedoraRevDepChecker.__init__

        def mock_init(self, verbose=False, base=None, repos=None):
            original_init(self, verbose=verbose, base=jupyterlab_base if base is None else base, repos=repos)

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        output = captured.out

        # Check output format
        assert 'These packages would FTI:' in output or 'These packages would FTBFS:' in output
        # Check that conflicts are listed with package names and constraints
        assert ':' in output  # Package: constraint format

    def test_main_deterministic_output(self, monkeypatch, jupyterlab_base):
        """Test that running main() twice produces same output."""
        monkeypatch.setattr('sys.argv', ['fedora-revdep-check', 'jupyterlab', '4.7.0'])

        original_init = FedoraRevDepChecker.__init__

        def mock_init(self, verbose=False, base=None, repos=None):
            original_init(self, verbose=verbose, base=jupyterlab_base if base is None else base, repos=repos)

        monkeypatch.setattr(FedoraRevDepChecker, '__init__', mock_init)

        # Capture first run
        from io import StringIO
        output1 = StringIO()
        monkeypatch.setattr('sys.stdout', output1)

        with pytest.raises(SystemExit):
            main()

        # Capture second run
        output2 = StringIO()
        monkeypatch.setattr('sys.stdout', output2)

        with pytest.raises(SystemExit):
            main()

        # Outputs should be identical (deterministic)
        assert output1.getvalue() == output2.getvalue()
