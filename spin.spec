Name:    spin
Version: 0.0
Release: 1%{?dist}
Summary: The Spin Package builds customized distributions

License:   GPLv2+
Group:     Applications/System
URL:       http://www.renditionsoftware.com/products/spin
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

BuildRequires: docbook-style-xsl
BuildRequires: gzip
BuildRequires: libxslt
BuildRequires: python-devel
BuildRequires: python-docutils

Requires: createrepo
Requires: netpbm-progs
Requires: python-devel
Requires: python-imaging
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: rpm-build
Requires: spin-logos-rpm
Requires: syslinux
Requires: yum

%description
The spin package contains the necessary shared server applications to build
and run a Spin-managed distribution.

%prep
%setup -q

%build
%{__make} depend

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR=%{buildroot}

%clean
%{__rm} -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root,-)
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%doc share/doc/examples
%exclude /usr/share/spin/release/eula.pyc
%exclude /usr/share/spin/release/eula.pyo
%{_mandir}/man5/spin.conf.5.gz
%{_mandir}/man5/distro.conf.5.gz
%{_mandir}/man1/spin.1.gz

%changelog
