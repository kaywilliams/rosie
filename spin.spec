%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    spin
Version: 0.8.15
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
Requires: dosfstools
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
* Tue Aug 05 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.15-1
- added brief note about <debug> element to spin.conf.xml (dmusgrave)
- bug 259 - added 'debug' to spin.conf schema (dmusgrave)
- added missing 'debug' attribute to spintest option instance (dmusgrave)
- (dmusgrave)
- fixed comps relative path for supplied comps file; fixed test pkglist format (dmusgrave)
- Tagged as spin-0.8.14-1 (uprakash)
- Bumped version to spin-0.8.14-1.noarch. (spinmaster)

* Fri Aug 01 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.14-1
- bug 253 - added newline between repogroup repos; fixed error messages for systemid (dmusgrave)
- bug 251 - better error message given with missing systemid (dmusgrave)
- added 'dosfstools' to INSTALL and spin.spec (dmusgrave)
- added repoid to various systemid error messages (dmusgrave)
- bug 249 - convert log-file to a string before opening for better error message (dmusgrave)
- bug 247 - pkglist validation improvements (dmusgrave)
- Fixed Bug 248. (uprakash)
- bug 241 - entering a systemid that is a directory => runtime error (dmusgrave)
- merged with trunk (dmusgrave)
- bug 245 - giving a non-file to <pkglist> no longer incorrectly results in (dmusgrave)
- repos/sources schemas now validate at least one repo or repofile element (kwilliams)
- comps.rng: whitespace fixup (kwilliams)
- bug 239 - no longer references obsolete <installer> element in anaconda RuntimeError (dmusgrave)
- added magic type check for gpgkeys prior to importing them into rpmdb (dmusgrave)
- bug 237 - pkglist now properly runs when included or excluded pkgs change (dmusgrave)
- merged with trunk (dmusgrave)
- bug 236 - rhn repos are now filtered from the yum repo file created in config-rpm (dmusgrave)
- If two configlets had the same key, the first one was being used. (uprakash)
- comps schema: validating that 'conditional' packages have 'requires' (kwilliams)
- PublishEvent triggers on changes to the 'selinux-enabled' variable. (uprakash)
- Chdir'ing into the config file's folder at a later point in time. (uprakash)
- diskboot-image rewrite - all diskboot images are now created from scratch (dmusgrave)
- config-rpm.rng: file)
- lib.rng: misc path attribute updates (kwilliams)
- Fixed Bug 231. (uprakash)
- Tagged as spin-0.8.13-1 (kwilliams)
- Bumped version to spin-0.8.13-1.noarch. (spinmaster)

* Wed Jul 23 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.13-1
- Tagged as spin-0.8.12-1 (kwilliams)
- Bumped version to spin-0.8.12-1.noarch. (spinmaster)

* Wed Jul 23 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.12-1
- Tagged as spin-0.8.11-1 (kwilliams)
- Bumped version to spin-0.8.11-1.noarch. (spinmaster)

* Wed Jul 23 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.11-1
- Tagged as spin-0.8.10-1 (kwilliams)
- Bumped version to spin-0.8.10-1.noarch. (spinmaster)

* Wed Jul 23 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.10-1
- Tagged as spin-0.8.9-1 (kwilliams)
- Bumped version to spin-0.8.9-1.noarch. (spinmaster)

* Wed Jul 23 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.9-1
- config-rpm: added web-path and gpgsign-public-key to variables diff data (kwilliams)
- added check to ensure systemid exists before trying to use it (dmusgrave)
- fixes for spintest (dmusgrave)
- merged with trunk (dmusgrave)
- modified schema to accept 4 digit modes (dmusgrave)
- config-rpm: bumped version number (kwilliams)
- Using IOMixin.sync_input(uprakash)
- Fixed a bug in logos-rpm which caused .pth files to not be read. (uprakash)
- fix to destname validation; allowing zero or more characters (kwilliams)
- branch merge (kwilliams)
- added validation for destname attribute; no '/' characters allowed (kwilliams)
- spin.spec: added requires for gnupg and mkisofs (kwilliams)
- dest -> destdir, filename -> destname in spintest (dmusgrave)
- updated .getpath(dmusgrave)
- Tagged as spin-0.8.8-1 (kwilliams)
- Bumped version to spin-0.8.8-1.noarch. (spinmaster)

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
