#!/usr/bin/env python3
"""
Fedora Reverse Dependency Checker

Checks if updating a package to a new version will break any reverse dependencies
in Fedora rawhide. Uses DNF Python bindings with cached repository data.

Usage:
    fedora-revdep-check <srpm-name> <new-version>

Example:
    fedora-revdep-check jupyterlab 4.7.0
"""

import sys
import re
import argparse
import operator
from collections import defaultdict
from typing import Dict, List, Tuple
import libdnf5
import rpm


# Mapping of RPM dependency operators to Python operator functions
OPERATOR_MAP = {
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
    '=': operator.eq,
    '==': operator.eq,
    '!=': operator.ne,
}


class FedoraRevDepChecker:
    """Check reverse dependencies for Fedora package updates."""

    def __init__(self, verbose=False, base=None, repos=None, releasever=None):
        """Initialize the checker with DNF base and cached repo data.

        Args:
            verbose: Enable verbose output
            base: Optional DNF base object for testing (if None, creates real DNF base)
            repos: List of repository IDs to enable (default: ['rawhide', 'rawhide-source', 'koji', 'koji-source'])
            releasever: Fedora release version (e.g. '44', 'rawhide'). Auto-detected from repos if not set.
        """
        self.verbose = verbose
        self.base = base
        self.releasever = releasever
        self.repos = repos if repos is not None else ['rawhide', 'rawhide-source', 'koji', 'koji-source']
        if self.base is None:
            self._init_dnf()

    def _get_known_repo_config(self, repo_id: str, releasever: str):
        """Get known repository configuration for common Fedora repos.

        Args:
            repo_id: Repository ID to configure
            releasever: Release version string

        Returns:
            Dictionary with 'metalink' or 'baseurl' key, or None if repo is not known
        """
        import re

        # Known repository configurations
        configs = {
            'rawhide': {
                'metalink': 'https://mirrors.fedoraproject.org/metalink?repo=rawhide&arch=$basearch'
            },
            'rawhide-source': {
                'metalink': 'https://mirrors.fedoraproject.org/metalink?repo=rawhide-source&arch=$basearch'
            },
            'koji': {
                'baseurl': 'https://kojipkgs.fedoraproject.org/repos/rawhide/latest/$basearch/'
            },
            'koji-source': {
                'baseurl': 'https://kojipkgs.fedoraproject.org/repos/rawhide/latest/src/'
            },
            'fedora': {
                'metalink': f'https://mirrors.fedoraproject.org/metalink?repo=fedora-{releasever}&arch=$basearch'
            },
            'fedora-source': {
                'metalink': f'https://mirrors.fedoraproject.org/metalink?repo=fedora-source-{releasever}&arch=$basearch'
            },
        }

        # Check exact match first
        if repo_id in configs:
            return configs[repo_id]

        # Pattern-based repository configurations
        # Each tuple: (regex_pattern, metalink_repo_template)
        patterns = [
            (r'^f(\d+)$', 'fedora-{version}'),
            (r'^f(\d+)-source$', 'fedora-source-{version}'),
            (r'^fedora-(\d+)$', 'fedora-{version}'),
            (r'^fedora-(\d+)-source$', 'fedora-source-{version}'),
        ]

        for pattern, repo_template in patterns:
            match = re.match(pattern, repo_id)
            if match:
                version = match.group(1)
                return {
                    'metalink': f'https://mirrors.fedoraproject.org/metalink?repo={repo_template.format(version=version)}&arch=$basearch'
                }

        return None

    def _init_dnf(self):
        """Initialize DNF 5 base and load repository metadata."""
        if self.verbose:
            print("Initializing DNF 5 and loading repository metadata...")
        self.base = libdnf5.base.Base()

        # Use explicitly provided releasever, or detect from repo names
        if self.releasever:
            releasever = self.releasever
        else:
            releasever = 'rawhide'
            if self.repos:
                first_repo = self.repos[0]
                import re
                version_match = re.search(r'(\d+)', first_repo)
                if version_match:
                    releasever = version_match.group(1)

        # Configure releasever
        vars_map = self.base.get_vars()
        vars_map.set('releasever', releasever)

        # Create repositories from system configuration
        repo_sack = self.base.get_repo_sack()
        repo_sack.create_repos_from_system_configuration()

        # Create repo query to manage repositories
        repo_query = libdnf5.repo.RepoQuery(self.base)

        # First, disable all repositories
        for repo in repo_query:
            repo.disable()

        # Track which repos were found in system config and which were created
        repos_from_config = set()
        repos_created = []

        # Enable specified repositories, create them if not found
        enabled_count = 0

        for repo_id in self.repos:
            # Filter for this specific repo ID
            specific_query = libdnf5.repo.RepoQuery(repo_query)
            specific_query.filter_id(repo_id)

            found = False
            for repo in specific_query:
                repo.enable()
                enabled_count += 1
                found = True
                repos_from_config.add(repo_id)
                if self.verbose:
                    print(f"  Enabled repo: {repo_id}")

            # If not found in system config, try to create it if we know the configuration
            if not found:
                repo_config = self._get_known_repo_config(repo_id, releasever)
                if repo_config:
                    try:
                        # Create the repository programmatically
                        repo = repo_sack.create_repo(repo_id)

                        # Configure the repository
                        config = repo.get_config()
                        if 'metalink' in repo_config:
                            config.metalink().set(libdnf5.conf.Option.Priority_RUNTIME, repo_config['metalink'])
                        elif 'baseurl' in repo_config:
                            config.baseurl = repo_config['baseurl']

                        # Disable GPG check for auto-created repos (following koji.repo pattern)
                        config.pkg_gpgcheck = "0"

                        # Enable the repo
                        repo.enable()
                        enabled_count += 1
                        repos_created.append(repo_id)

                        if self.verbose:
                            print(f"  Created and enabled repo: {repo_id} (using default configuration)")
                    except Exception as e:
                        if self.verbose:
                            import traceback
                            print(traceback.format_exc())
                            print(f"  Warning: Failed to create repository '{repo_id}': {e}")
                elif self.verbose:
                    print(f"  Warning: Repository '{repo_id}' not found in configuration and no default available")

        # Show warning if any repos were auto-created
        if repos_created and self.verbose:
            print(f"Warning: Using default configuration for repositories: {', '.join(repos_created)}")
            print("         Consider installing the repository configuration in /etc/yum.repos.d/")

        if enabled_count == 0:
            raise RuntimeError(
                f"Failed to enable any repositories from: {', '.join(self.repos)}. "
                "Please ensure the repositories are configured in /etc/yum.repos.d/ or use known repository IDs."
            )

        if self.verbose:
            print(f"Enabled {enabled_count} repository/repositories")

        # Setup the base before loading repos
        self.base.setup()

        # Load repository metadata
        if self.verbose:
            print("Loading repository metadata (this may take a moment)...")
        repo_sack.load_repos()
        if self.verbose:
            print("Repository metadata loaded and cached.")

    def get_binary_packages(self, srpm_name: str) -> List[libdnf5.rpm.Package]:
        """Get all binary packages built from the given SRPM."""
        query = libdnf5.rpm.PackageQuery(self.base)

        # Find packages with matching source name (first pass)
        matching_names = []
        for pkg in query:
            if pkg.get_source_name() == srpm_name:
                matching_names.append(pkg.get_name())

        if not matching_names:
            if self.verbose:
                print(f"Searched for packages from source '{srpm_name}'")
                print("  No packages found. Checking if source package exists...")
                # Try to find if there's a similarly named package
                name_query = libdnf5.rpm.PackageQuery(self.base)
                name_query.filter_name([srpm_name])
                for p in name_query:
                    print(f"  Found binary package '{p.get_name()}' with source_name='{p.get_source_name()}'")
            return []

        # Get unique package names
        unique_names = list(set(matching_names))

        # Create a new query for these specific packages
        result_query = libdnf5.rpm.PackageQuery(self.base)
        result_query.filter_name(unique_names)

        # Filter to latest versions only
        result_query.filter_latest_evr()

        # Deduplicate by NEVRA and filter out source packages
        seen_nevra = set()
        unique_packages = []
        for pkg in result_query:
            # Skip source packages (we only want binary packages for dependency checking)
            if pkg.get_arch() == 'src':
                continue

            nevra = f"{pkg.get_name()}-{pkg.get_epoch()}:{pkg.get_version()}-{pkg.get_release()}.{pkg.get_arch()}"
            if nevra not in seen_nevra:
                seen_nevra.add(nevra)
                unique_packages.append(pkg)

        if self.verbose:
            print(f"Searched for packages from source '{srpm_name}'")
            print(f"  Found {len(unique_names)} unique package name(s), filtered to latest versions")

        return unique_packages

    def get_provides(self, package: libdnf5.rpm.Package) -> List[Tuple[str, str]]:
        """
        Get all provides from a package, filtering out bundled provides.

        Returns list of (provide_name, provide_version, provide_str) tuples.
        """
        provides = []
        for prv in package.get_provides():
            provide_str = prv.to_string()

            # Skip bundled provides
            if provide_str.startswith('bundled('):
                continue

            # Parse provide into name and version
            # Format can be: "name = version", "name >= version", "name", etc.
            match = re.match(r'^([^\s<>=]+)\s*(?:([<>=]+)\s*(.+))?$', provide_str)
            if match:
                provide_name = match.group(1)
                provide_version = match.group(3) if match.group(3) else None
                provides.append((provide_name, provide_version, provide_str))

        return provides

    def find_reverse_dependencies(self, provide_name: str) -> List[libdnf5.rpm.Package]:
        """Find all packages that require the given provide."""
        query = libdnf5.rpm.PackageQuery(self.base)

        # Filter packages that require this provide
        query.filter_requires([provide_name])

        # Filter to latest versions only to avoid duplicates from multiple repos/versions
        query.filter_latest_evr()

        return list(query)

    def simulate_version_change(self, srpm_name: str, new_version: str) -> Dict:
        """
        Simulate updating the package to a new version and check for conflicts.

        Returns a dictionary with conflict information.
        """
        if self.verbose:
            print(f"\nAnalyzing impact of updating {srpm_name} to version {new_version}...\n")

        # Get all binary packages from this SRPM
        binary_packages = self.get_binary_packages(srpm_name)

        if not binary_packages:
            return {
                'error': f"No packages found for source package: {srpm_name}",
                'binary_packages': []
            }

        # If new_version doesn't include an epoch, inherit it from current packages
        if ':' not in new_version:
            # Get epoch from first package (all packages from same SRPM should have same epoch)
            current_epoch = binary_packages[0].get_epoch()
            if current_epoch and current_epoch != '0':
                new_version = f"{current_epoch}:{new_version}"
                if self.verbose:
                    print(f"No epoch specified in new version, using epoch {current_epoch} from current package")
                    print(f"Testing with version: {new_version}\n")

        if self.verbose:
            print(f"Found {len(binary_packages)} binary package(s) from {srpm_name}:")
            for pkg in binary_packages:
                print(f"  - {pkg.get_name()}-{pkg.get_version()}-{pkg.get_release()}")
            print()

        # Collect all provides from all binary packages
        all_provides = defaultdict(list)  # provide_name -> [(pkg, provide_str, old_version)]

        for pkg in binary_packages:
            provides = self.get_provides(pkg)
            if self.verbose:
                print(f"Package {pkg.get_name()} has {len(provides)} provides (excluding bundled)")
            for prov_name, prov_version, prov_str in provides:
                all_provides[prov_name].append((pkg, prov_str, prov_version))

        if self.verbose:
            print(f"Found {len(all_provides)} unique provides (excluding bundled)")
            for prov_name in sorted(all_provides.keys()):
                print(f"  - {prov_name}")
            print()

        # For each provide, find reverse dependencies and check conflicts
        conflicts = []
        checked_requirements = set()  # Track (pkg_key, req_str) to avoid duplicates

        for prov_name, prov_info_list in all_provides.items():
            rdeps = self.find_reverse_dependencies(prov_name)

            if self.verbose and rdeps:
                print(f"Provide '{prov_name}' has {len(rdeps)} reverse dependencies")

            if not rdeps:
                continue

            for rdep_pkg in rdeps:
                # Skip packages from the same SRPM - they'll be updated together
                if rdep_pkg.get_source_name() == srpm_name:
                    if self.verbose:
                        print(f"  Skipping {rdep_pkg.get_name()} (from same SRPM: {srpm_name})")
                    continue

                pkg_key = f"{rdep_pkg.get_name()}-{rdep_pkg.get_version()}-{rdep_pkg.get_release()}"

                # Check if this package's requirements would be satisfied with new version
                for req in rdep_pkg.get_requires():
                    req_str = req.to_string()

                    # Check if this requirement mentions our provide
                    # We need precise matching to avoid false positives like
                    # "pytest" matching "pytest-xdist" or "python3dist(pytest-xdist)"
                    if not self._requirement_matches_provide(req_str, prov_name):
                        continue

                    # Avoid checking the same requirement multiple times
                    check_key = (pkg_key, req_str)
                    if check_key in checked_requirements:
                        continue
                    checked_requirements.add(check_key)

                    if self.verbose:
                        print(f"  Checking: {rdep_pkg.get_name()} requires {req_str}")

                    # Check if the new version would satisfy this requirement
                    conflict = self._check_requirement_conflict(
                        req_str, prov_name, new_version, rdep_pkg, prov_info_list
                    )

                    if conflict:
                        conflicts.append(conflict)
                        if self.verbose:
                            print(f"    -> CONFLICT: {conflict['failed_constraint']}")

        return {
            'srpm_name': srpm_name,
            'new_version': new_version,
            'binary_packages': [f"{pkg.get_name()}-{pkg.get_version()}-{pkg.get_release()}" for pkg in binary_packages],
            'conflicts': conflicts
        }

    def _requirement_matches_provide(self, req_str: str, prov_name: str) -> bool:
        """
        Check if a requirement string actually references the given provide.

        This does precise matching to avoid false positives like:
        - "pytest" matching "pytest-xdist"
        - "python3dist(pytest)" matching "python3dist(pytest-xdist)"

        Args:
            req_str: Requirement string (e.g., "python3dist(pytest) >= 4")
            prov_name: Provide name to check (e.g., "python3dist(pytest)")

        Returns:
            True if the requirement references this provide, False otherwise
        """
        req_clean = req_str.strip()

        # Handle rich dependencies starting with parentheses
        if req_clean.startswith('('):
            # Remove outer parentheses
            req_clean = req_clean[1:-1] if req_clean.endswith(')') else req_clean[1:]

            # Split by boolean operators (with, if, unless, or, and)
            # We need to check if any of the parts match our provide
            parts = re.split(r'\s+(?:with|if|unless|or|and)\s+', req_clean)

            for part in parts:
                # Each part should be like "name op version" or just "name"
                # Extract the name (first token before any operator)
                match = re.match(r'^([^\s<>=]+)', part.strip())
                if match and match.group(1) == prov_name:
                    return True
            return False
        else:
            # Simple requirement, must start with the provide name
            # followed by whitespace, operator, or end of string
            # This prevents "pytest" from matching "pytest-xdist"
            if req_str.startswith(prov_name):
                # Check what comes after the provide name
                if len(req_str) == len(prov_name):
                    return True  # Exact match
                next_char = req_str[len(prov_name)]
                # Must be followed by space, comparison operator, exclamation (for !=), or parenthesis close
                return next_char in ' <>=()\t!'
            return False

    def _check_requirement_conflict(
        self, req_str: str, prov_name: str, new_version: str,
        rdep_pkg: libdnf5.rpm.Package, prov_info_list: List
    ) -> Dict:
        """
        Check if a requirement would conflict with the new version.

        Returns conflict info dict if there's a conflict, None otherwise.
        """
        # Parse the requirement string to extract constraints
        # Format examples:
        #   "python3dist(jupyterlab) >= 4.5~rc0"
        #   "(python3dist(jupyterlab) >= 4 with python3dist(jupyterlab) < 5)"
        #   "python3dist(jupyterlab) < 4.6~~"

        # Handle rich dependencies (with "with", "if", "unless")
        if ' with ' in req_str or ' if ' in req_str or ' unless ' in req_str:
            # For now, we'll parse "with" clauses
            # This is a simplified parser for common cases
            constraints = []

            # Remove outer parentheses
            req_clean = req_str.strip()
            if req_clean.startswith('(') and req_clean.endswith(')'):
                req_clean = req_clean[1:-1]

            # Split by "with" to get multiple constraints
            parts = re.split(r'\s+with\s+', req_clean)
            for part in parts:
                match = re.match(r'([^\s<>=]+)\s*([<>=]+)\s*(.+)', part.strip())
                if match and match.group(1) == prov_name:
                    constraints.append({
                        'name': match.group(1),
                        'op': match.group(2),
                        'version': match.group(3)
                    })
        else:
            # Simple constraint
            match = re.match(r'([^\s<>=]+)\s*([<>=]+)\s*(.+)', req_str.strip())
            if match and match.group(1) == prov_name:
                constraints = [{
                    'name': match.group(1),
                    'op': match.group(2),
                    'version': match.group(3)
                }]
            else:
                # No version constraint, just package name
                constraints = []

        # Check if new version satisfies all constraints
        if constraints:
            for constraint in constraints:
                # Determine which new version to use based on whether the provide uses epochs
                # Check if any current provide has an epoch in its version
                provide_uses_epoch = False
                for pkg, prov_str, prov_version in prov_info_list:
                    current_ver = prov_version if prov_version else pkg.get_version()
                    if ':' in current_ver:
                        provide_uses_epoch = True
                        break

                # Use appropriate version: with or without epoch depending on provide format
                version_to_check = new_version if provide_uses_epoch else new_version.split(':', 1)[-1]

                if not self._version_satisfies(version_to_check, constraint['op'], constraint['version']):
                    # New version fails - now check if current version also fails
                    # to determine if this is a new problem or already broken
                    current_version_also_fails = False

                    # Get current version from prov_info_list
                    for pkg, prov_str, prov_version in prov_info_list:
                        # Use the package version if provide doesn't have its own version
                        current_ver = prov_version if prov_version else pkg.get_version()
                        if not self._version_satisfies(current_ver, constraint['op'], constraint['version']):
                            current_version_also_fails = True
                            break

                    return {
                        'rdep_package': f"{rdep_pkg.get_name()}-{rdep_pkg.get_version()}-{rdep_pkg.get_release()}",
                        'rdep_source': rdep_pkg.get_source_name(),
                        'rdep_arch': rdep_pkg.get_arch(),
                        'requirement': req_str,
                        'provide_name': prov_name,
                        'new_version': new_version,
                        'failed_constraint': f"{prov_name} {constraint['op']} {constraint['version']}",
                        'already_broken': current_version_also_fails
                    }

        return None

    def _version_satisfies(self, version: str, op: str, required_version: str) -> bool:
        """
        Check if a version satisfies a requirement using RPM version comparison.

        Uses rpm.labelCompare which understands RPM versioning including
        tilde (~) for pre-releases and caret (^) for post-releases.
        """
        # Parse versions into (epoch, version, release) tuples
        # If no epoch or release is specified, use defaults
        def parse_evr(ver_str):
            """Parse a version string into (epoch, version, release) tuple."""
            epoch = None
            version = ver_str
            release = None

            # Check for epoch (e.g., "1:2.3.4-1")
            if ':' in ver_str:
                epoch_str, rest = ver_str.split(':', 1)
                epoch = epoch_str
                ver_str = rest

            # Check for release (e.g., "2.3.4-1")
            if '-' in ver_str:
                version, release = ver_str.rsplit('-', 1)
            else:
                version = ver_str

            # rpm.labelCompare expects strings or None
            return (epoch or '0', version, release or '0')

        evr1 = parse_evr(version)
        evr2 = parse_evr(required_version)

        # rpm.labelCompare returns -1, 0, or 1
        cmp_result = rpm.labelCompare(evr1, evr2)

        # Get the comparison function from the mapping
        op_func = OPERATOR_MAP.get(op)
        if op_func:
            result = op_func(cmp_result, 0)
        else:
            # Unknown operator
            result = False

        if self.verbose:
            print(f"      Version check: {version} {op} {required_version} => {result} (cmp={cmp_result})")

        return result

    def print_results(self, results: Dict):
        """Print analysis results in a readable format."""
        if 'error' in results:
            print(f"ERROR: {results['error']}")
            return

        conflicts = results['conflicts']

        if not conflicts:
            if self.verbose:
                print(f"No conflicts detected for {results['srpm_name']} {results['new_version']}")
        else:
            # Separate conflicts by type and whether they're new or already broken
            ftbfs_new = []
            ftbfs_already_broken = []
            fti_new = []
            fti_already_broken = []

            for conflict in conflicts:
                is_source = conflict['rdep_arch'] == 'src'
                is_already_broken = conflict.get('already_broken', False)

                if is_source:
                    if is_already_broken:
                        ftbfs_already_broken.append(conflict)
                    else:
                        ftbfs_new.append(conflict)
                else:
                    if is_already_broken:
                        fti_already_broken.append(conflict)
                    else:
                        fti_new.append(conflict)

            # Print new FTBFS conflicts
            if ftbfs_new:
                print("These packages would FTBFS:")
                for conflict in ftbfs_new:
                    package_name = conflict['rdep_source']
                    print(f"  {package_name}: {conflict['failed_constraint']}")

            # Print new FTI conflicts
            if fti_new:
                if ftbfs_new:
                    print()  # Empty line between sections
                print("These packages would FTI:")
                for conflict in fti_new:
                    package_name = conflict['rdep_package']
                    print(f"  {package_name}: {conflict['failed_constraint']}")

            # Print already broken FTBFS packages
            if ftbfs_already_broken:
                if ftbfs_new or fti_new:
                    print()  # Empty line between sections
                print("These packages already FTBFS (not a new problem):")
                for conflict in ftbfs_already_broken:
                    package_name = conflict['rdep_source']
                    print(f"  {package_name}: {conflict['failed_constraint']}")

            # Print already broken FTI packages
            if fti_already_broken:
                if ftbfs_new or fti_new or ftbfs_already_broken:
                    print()  # Empty line between sections
                print("These packages already FTI (not a new problem):")
                for conflict in fti_already_broken:
                    package_name = conflict['rdep_package']
                    print(f"  {package_name}: {conflict['failed_constraint']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check reverse dependencies for Fedora package updates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s jupyterlab 4.7.0
  %(prog)s python-requests 2.32.0 --verbose
  %(prog)s pytest 8.0.0 --repo fedora --repo fedora-source
  %(prog)s numpy 2.0.0 --repo fedora-40 --repo fedora-40-source
  %(prog)s pytest 8.0.0 --releasever 44
        """
    )

    parser.add_argument('srpm_name', help='Source package name (SRPM)')
    parser.add_argument('new_version', help='New version to test')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-r', '--repo', action='append', dest='repos',
                        help='Repository ID to enable (can be specified multiple times). '
                             'Default: rawhide, rawhide-source, koji, and koji-source. '
                             'Known repositories will be auto-configured if not in /etc/yum.repos.d/')
    parser.add_argument('--releasever',
                        help='Fedora release version (e.g. 44, rawhide). '
                             'Auto-detected from repo names if not specified.')

    args = parser.parse_args()

    try:
        checker = FedoraRevDepChecker(verbose=args.verbose, repos=args.repos, releasever=args.releasever)
        results = checker.simulate_version_change(args.srpm_name, args.new_version)
        checker.print_results(results)

        # Exit with error code if NEW conflicts found (not already-broken packages)
        if results.get('conflicts'):
            # Check if there are any new conflicts (not already broken)
            has_new_conflicts = any(
                not conflict.get('already_broken', False)
                for conflict in results['conflicts']
            )
            if has_new_conflicts:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
