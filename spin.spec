%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    spin
Version: 0.8.34
Release: 1%{?dist}
Summary: The Spin Package builds customized appliances

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
Requires: rhn-client-tools
Requires: rpm-build
Requires: spin-logos
Requires: syslinux
Requires: yum

%description
The spin package contains the necessary shared server applications to build
and run a Spin-managed appliance.

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
%exclude /usr/share/spin/release/eula.pyc
%exclude /usr/share/spin/release/eula.pyo
%{_mandir}/man5/spin.conf.5.gz
%{_mandir}/man1/spin.1.gz

%changelog
* Tue Aug 26 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.34-1
- ImageModifyMixin now checks the format of images before adding them (dmusgrave)
- changed file format keys to use magic constants (dmusgrave)
- allow multiple baseurls per repo in lib.rng (dmusgrave)
- moved adding of cvars['repos'] to .setup(dmusgrave)
- Tagged as spin-0.8.33-1 (uprakash)
- Bumped version to spin-0.8.33-1.noarch. (spinmaster)

* Mon Aug 25 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.33-1
- Fixed version in setup.py. (uprakash)
- Tagged as spin-0.8.32-1 (uprakash)
- Bumped version to spin-0.8.32-1.noarch. (spinmaster)

* Mon Aug 25 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.32-1
- removed unnecessary RNG files (dmusgrave)
- removed comps.xml data from createrepo locals; since comps.xml isn't a 'core' part of a repository, it doesn't make sense to include (dmusgrave)
- Fixed version in setup.py. (uprakash)
- Being smarter about package updates; code cleanup. (uprakash)
- Tagged as spin-0.8.31-1 (uprakash)
- Bumped version to spin-0.8.31-1.noarch. (spinmaster)

* Fri Aug 22 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.31-1
- fixed checksumming error for RepoGroups (dmusgrave@renditionsoftware.com)
- bug 283 - added repomd checksumming after download; merged with trunk (dmusgrave)
- bug 283 - added repomd checksumming after download (dmusgrave)
- Fixed version in setup.py. (uprakash)
- Tagged as spin-0.8.30-1 (uprakash)
- Bumped version to spin-0.8.30-1.noarch. (spinmaster)

* Thu Aug 21 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.30-1
- Extracting RPMs iff )
- bug 288 - comps wasn't including all group data in some situations (dmusgrave)
- removed the ability to supply pkgorder and pkglists via config; they now must be dynamically generated (dmusgrave)
- corrected iso boot-config test cases to use 'use-defaults' instead of 'use-default' (dmusgrave)
- updated release-files test case with new attribute name; corrected Test_ReleaseFilesWithDefaultSet test cases (dmusgrave)
- changed release-files/)
- fixed a bug where shared/rpmbuild.py was checking use-default-set while the rng had use-default-obsoletes (dmusgrave)
- removed additional extranneous stuff from isolinux.rng (dmusgrave)
- fixed eth0 bug in automatic interface detection code in publish (dmusgrave)
- merged with trunk (dmusgrave)
- added missing (dmusgrave)
- updated pid file handling to newer cachedir location (dmusgrave)
- changed ImageModifyMixin.clean_eventcache(dmusgrave)
- Bumped the logos-rpm event version. (uprakash)
- Fixed the firstboot triggerin script. (uprakash)
- <arch> is now required element within <main> (dmusgrave)
- added basearch,releasever to sources for repos parity (dmusgrave)
- Made PublishSetupEvent.remote and PublishSetupEvent.local Path objects. (uprakash)
- default publish locations now include a "prefix" again (dmusgrave)
- creating cache dir before trying to lock (dmusgrave)
- Fixed version in setup.py. (uprakash)
- Tagged as spin-0.8.29-1 (uprakash)
- Bumped version to spin-0.8.29-1.noarch. (spinmaster)

* Mon Aug 18 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.29-1
- fixing issues with schemas in 'distro' => 'appliance' folders (dmusgrave)
- correcting update issues with schemas in 'distro' and 'application' folders (dmusgrave)
- various updates to publish (dmusgrave)
- removed erroneous conditionally-requires for 'isolinux' event (dmusgrave)
- spin locking is now done by cache folder instead of globally; this allows you to run multiple copies of spin with different cache locations (dmusgrave)
- removed erroneous 'boot-args' argument (dmusgrave)
- fixed a bug with ShLibErrors not being __init__(dmusgrave)
- Fixed release number in setup.py. (uprakash)
- Tagged as spin-0.8.28-1 (uprakash)
- Bumped version to spin-0.8.28-1.noarch. (spinmaster)

* Mon Aug 18 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.28-1
- Whitespace cleanup. (uprakash)
- Added spintest/test.log to .hgignore. (uprakash)
- Had accidentally added test.log to the repository. (uprakash)
- wording tweaks to INSTALL file (kwilliams)
- Changed all references of "distro" to "appliance". (uprakash)
- Tagged as spin-0.8.27-1 (uprakash)
- Bumped version to spin-0.8.27-1.noarch. (spinmaster)

* Mon Aug 18 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.27-1
- Fixed release number in setup.py. (uprakash)
- Tagged as spin-0.8.26-1 (uprakash)
- Bumped version to spin-0.8.26-1.noarch. (spinmaster)

* Fri Aug 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.26-1
- Tagged as spin-0.8.25-1 (uprakash)
- Bumped version to spin-0.8.25-1.noarch. (spinmaster)

* Fri Aug 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.25-1
- Fixed usernames in spec file's changelog entry. (uprakash)
- Fixed changelog entry in spec file. (uprakash)
- Tagged as spin-0.8.24-1 (root@server2.renditionsoftware.com)
- Bumped version to spin-0.8.24-1.noarch. (spinmaster)

* Fri Aug 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.24-1
- Tagged as spin-0.8.23-1 (uprakash)
- Bumped version to spin-0.8.23-1.noarch. (spinmaster)

* Fri Aug 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.23-1
- Tagged as spin-0.8.22-1 (uprakash)
- Bumped version to spin-0.8.22-1.noarch. (uprakash)

* Thu Aug 14 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.22-1
- Fixed Bug 284. (uprakash)
- Fixed Bug 290. (uprakash)
- Renamed IDepsolverCallback to TimerCallback. (uprakash)
- Spin doesn't require rhnlib explicitly. (uprakash)
- Tagged as spin-0.8.21-1 (uprakash)
- Bumped version to spin-0.8.21-1.noarch. (uprakash)

* Tue Aug 12 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.21-1
- Tagged as spin-0.8.20-1 (uprakash)
- Bumped version to spin-0.8.20-1.noarch. (uprakash)

* Tue Aug 12 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.20-1
- Spin now requires rhnlin, rhn-client-tools, and spin-logos. (uprakash)
- oops, remove extraneous single quote from last commit (kwilliams)
- buildstamp bugfix - added packagepath, removed name from diff variables (kwilliams)
- updated comps validation so it fails if it doesn't contain text(dmusgrave)
- infofiles: small fix, added missing comma (kwilliams)
- Bumped treeinfo event's version number. (uprakash)
- The .treeinfo file had the wrong arch being written. (uprakash)
- The 'pkglist' event prints out warnings for user-required packages. (uprakash)
- Fixed printout of warnings in pkglist event. (uprakash)
- Fixed Bug 205. (uprakash)
- Tagged as spin-0.8.19-1 (kwilliams)
- Bumped version to spin-0.8.19-1.noarch. (spinmaster)

* Fri Aug 08 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.19-1
- bug 280 - fixed incorrectly named exception (dmusgrave)
- various fileio improvements; fixed gpgsign valid key -> exception bug (dmusgrave)
- bug 276 - missing gpgkeys to gpgsign now show up in gpgsign-setup rather than config-rpm (dmusgrave)
- bugfix to logic processing of debug flags that prevented --no-debug from working (dmusgrave)
- bug 243 - gpgsign fixed up so errors are handled (dmusgrave)
- bug 250, bug 274 - empty repofiles now error; invalid repofiles errors are handled (dmusgrave)
- error raised by .io.add_*(dmusgrave)
- minor change to pkglist Supplied test case to ensure path is computed correctly (dmusgrave)
- Tagged as spin-0.8.18-1 (kwilliams)
- Bumped version to spin-0.8.18-1.noarch. (spinmaster)

* Thu Aug 07 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.18-1
- main: log messages now refer to distro 'definition' file rather than (kwilliams)
- wrapped log creation and config getting code in exception handlers to prevent tracebacks (dmusgrave)
- slightly optimized SpinErrorHandler.handle_Exception code path (dmusgrave)
- pulled out validation code from main.py into validate.py (dmusgrave)
- improved non debug mode output handling; except SpinErrors explicitly (dmusgrave)
- bug 261 - pkglist depsolve errors are now 'handled' errors (dmusgrave)
- bug 240 - invalid systemids no longer show up as unhandled (dmusgrave)
- If mkrpm.verifyRpms(uprakash)
- bug 267 - error messages now always start on a new line (dmusgrave)
- merged with trunk (dmusgrave)
- various bugs - allow reporting of errors to use the source, rather than the cached location (dmusgrave)
- added missing import of assert_file_readable (dmusgrave)
- The GpgCheckEvent.gpgkeys attribute is no longer there. (uprakash)
- Fixed Bug 268. (uprakash)
- Fixed bug in triggerun scriptlet for firstboot. (uprakash)
- Tagged as spin-0.8.17-1 (kwilliams)
- Bumped version to spin-0.8.17-1.noarch. (spinmaster)

* Tue Aug 05 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.17-1
- The logos RPM's triggerin on firstboot, copies instead of linking. (uprakash)
- various fixes to error system and spintest integration (dmusgrave)
- Fixed Bug 263; another miscellaneous cleanup of docs. (uprakash)
- minor edits to spin.conf.xml for consistency (kwilliams)
- adding quotes to log message for clarity (kwilliams)
- gpgsign: rearranged actions in run event (kwilliams)
- Fixed Bug 260. (uprakash)
- Made the GpgCheckEvent.version a string. (uprakash)
- Not raising an AttributeError, if RhnPath is not defined. (uprakash)
- Tagged as spin-0.8.16-1 (kwilliams)
- Bumped version to spin-0.8.16-1.noarch. (spinmaster)

* Tue Aug 05 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.16-1
- Tagged as spin-0.8.15-1 (kwilliams)
- Bumped version to spin-0.8.15-1.noarch. (spinmaster)

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
- Tagged as spin-0.8.2-1 (uprakash)
- spin-0.8.2-1.noarch built. (uprakash)

* Tue Jul 15 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.2-1
- Tagged as spin-0.8.1-1 (kwilliams)
- spin-0.8.1-1.noarch built. (kwilliams)

* Mon Jul 14 2008 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- Initial Build
