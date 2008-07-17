Name:    spin
Version: 0.8.4
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
BuildRequires: python-setuptools
BuildRequires: python-docutils

Requires: createrepo
Requires: netpbm-progs
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
%config(noreplace) %{_sysconfdir}/logrotate.d/spin
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
* Tue Jul 15 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.4-1
- Tagged as spin-0.8.3-1 (kwilliams)
- Bumped version to spin-0.8.3-1.noarch. (spinmaster)

* Tue Jul 15 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.3-1
- ChangeLog updated as part of `make bumpver' (uprakash)
- Reverted to 0.8.2-1 (uprakash)
- Tagged as spin-0.8.3-1 (uprakash)
- Built package spin-0.8.3-1.noarch. (spinmaster)
- Bumped version to spin-0.8.3-1.noarch. (spinmaster)
- Adding user name and email address to changelog. (uprakash)
- Tagged as spin-0.8.2-1 (root@localhost.localdomain)
- spin-0.8.2-1.noarch built. (root@localhost.localdomain)

* Tue Jul 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.2-1
- Tagged as spin-0.8.1-1 (kwilliams)
- spin-0.8.1-1.noarch built. (kwilliams)

* Mon Jul 14 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- Initial Build

