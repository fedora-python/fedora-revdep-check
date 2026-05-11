#!/usr/bin/env bash
# Rebuild all test RPM fixtures from the spec files in specs/.
# Run this script when you add a new spec or need to regenerate existing RPMs.
#
# Requirements: rpmbuild

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT

build_binary() {
    rpmbuild --define "_topdir $BUILD" --define "dist %{nil}" --nodeps -bb "$1" 2>&1
}

build_source() {
    rpmbuild --define "_topdir $BUILD" --define "dist %{nil}" --nodeps -bs "$1" 2>&1
}

for spec in "$SCRIPT_DIR"/specs/*.spec; do
    echo "Building binary: $spec"
    build_binary "$spec"
done

echo "Building source RPM: revdeptest-foo.spec"
build_source "$SCRIPT_DIR/specs/revdeptest-foo.spec"

cp "$BUILD"/RPMS/noarch/*.rpm "$SCRIPT_DIR"/
cp "$BUILD"/SRPMS/*.rpm       "$SCRIPT_DIR"/

echo ""
echo "Built RPMs:"
ls -lh "$SCRIPT_DIR"/*.rpm
