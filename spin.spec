%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    spin
Version: 0.8.8
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
BuildRequires: python-setuptools
BuildRequires: python-docutils

Requires: createrepo
Requires: gnupg
Requires: mkisofs
Requires: netpbm-progs
Requires: python-devel
Requires: python-imaging
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: rpm-build
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

%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/logrotate.d/spin
%dir %{python_sitelib}/spin
%dir %{python_sitelib}/spin/event
%dir %{python_sitelib}/spin/locals
%dir %{python_sitelib}/spin/modules
%dir %{python_sitelib}/spin/modules/core
%dir %{python_sitelib}/spin/modules/core/installer
%dir %{python_sitelib}/spin/modules/core/packages
%dir %{python_sitelib}/spin/modules/core/rpmbuild
%dir %{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm
%dir %{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm/config
%dir %{python_sitelib}/spin/modules/extensions
%dir %{python_sitelib}/spin/modules/extensions/installer
%dir %{python_sitelib}/spin/modules/extensions/packages
%dir %{python_sitelib}/spin/modules/shared
%dir %{_datadir}/spin
%{python_sitelib}/spin/*.py*
%{python_sitelib}/spin/event/*.py*
%{python_sitelib}/spin/locals/*.py*
%{python_sitelib}/spin/modules/*.py*
%{python_sitelib}/spin/modules/core/*.py*
%{python_sitelib}/spin/modules/core/installer/*.py*
%{python_sitelib}/spin/modules/core/packages/*.py*
%{python_sitelib}/spin/modules/core/rpmbuild/*.py*
%{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm/*.py*
%{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm/config/*.py*
%{python_sitelib}/spin/modules/extensions/*.py*
%{python_sitelib}/spin/modules/extensions/installer/*.py*
%{python_sitelib}/spin/modules/extensions/packages/*.py*
%{python_sitelib}/spin/modules/shared/*.py*
%{_bindir}/spin
%{_datadir}/spin
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
* Wed Jul 16 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.8-1
- After a lot of testing, now finally requiring 'python-devel'. (uprakash)
- Tagged as spin-0.8.7-1 (kwilliams)
- Bumped version to spin-0.8.7-1.noarch. (spinmaster)

* Wed Jul 16 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.7-1
- Requiring python instead of python-devel. (uprakash)
- Tagged as spin-0.8.6-1 (kwilliams)
- Bumped version to spin-0.8.6-1.noarch. (spinmaster)

* Wed Jul 16 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.6-1
- merged with trunk. (uprakash)
- I lied, python-devel is required. (uprakash)
- Tagged as spin-0.8.5-1 (kwilliams)
- Bumped version to spin-0.8.5-1.noarch. (spinmaster)

* Wed Jul 16 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.5-1
- Changed dest to destdir and filename and destname in config-rpm. (uprakash)
- Renamed <path/> element attributes. (uprakash)
- Spin now owns /usr/share/spin. (uprakash)
- You can now have files with extension .pth in <share>/logos-rpm. (uprakash)
- Spin doesn't require spin-logos-rpm. It is optional. (uprakash)
- Not relying on INSTALLED_FILES; using globs in %files in spec file. (uprakash)
- Removing empty extensions/rpmbuild folder. (uprakash)
- Removing dependency on 'python-devel'. (uprakash)
- Was re-installing /etc/* files. (uprakash)
- execlib --> shlib. (uprakash)
- removed erroneous Macro import (dmusgrave)
- applied .getbool(dmusgrave)
- merged with head. (uprakash)
- The 'publish' event cleans up files and directories in output folder. (uprakash)
- Tagged as spin-0.8.4-1 (kwilliams)
- Bumped version to spin-0.8.4-1.noarch. (spinmaster)

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
