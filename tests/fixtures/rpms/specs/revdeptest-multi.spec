Name:           revdeptest-multi
Version:        1.0
Release:        1
Summary:        Test package with subpackage for fedora-revdep-check tests
License:        CC0-1.0
BuildArch:      noarch

Provides:       python3dist(revdeptest-multi) = 1.0

%description
Main test package with a subpackage for fedora-revdep-check unit tests.

%package sub
Summary:        Subpackage of revdeptest-multi
BuildArch:      noarch

Provides:       python3dist(revdeptest-multi-sub) = 1.0

%description sub
Subpackage for fedora-revdep-check unit tests.

%install

%files

%files sub

%changelog
