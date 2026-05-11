Name:           revdeptest-bundled
Version:        1.0
Release:        1
Summary:        Test package with bundled provides for fedora-revdep-check tests
License:        CC0-1.0
BuildArch:      noarch

Provides:       bundled(libfoo) = 2.0
Provides:       bundled(libbar) = 3.0

%description
Minimal test package with bundled provides for fedora-revdep-check unit tests.

%install

%files

%changelog
