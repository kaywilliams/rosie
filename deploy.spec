%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    deploy
Version: 2.1
Release: 43%{?dist}
Summary: An open platform for managing system and application deployment.

License:   GPL
Group:     Applications
URL:       http://www.deployproject.org
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

BuildRequires: docbook-style-xsl
BuildRequires: gzip
BuildRequires: libxml2
BuildRequires: libxslt
BuildRequires: python

Requires: createrepo
Requires: dosfstools
Requires: gnupg
Requires: gzip 
Requires: isomd5sum 
Requires: mkisofs
Requires: openssh 
Requires: pexpect
Requires: pykickstart
Requires: python-devel
Requires: python-hashlib
Requires: python-lxml
Requires: python-setuptools
Requires: rpmdevtools
Requires: rng-tools
Requires: rpm-build
Requires: syslinux
Requires: yum
Requires: xz
Requires: /usr/bin/rpmsign
Requires: /usr/bin/sudo

%description
Deploy is an open source, community-based platform for managing system and
application deployment. See http://www.deployproject.org for more information. 

%prep
%setup -q

%build
%{__make}

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/deploy/deploy.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/deploy
%{python_sitelib}/*
%{_bindir}/deploy
%{_datadir}/deploy
%doc COPYING
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/deploy.conf.5.gz
%{_mandir}/man1/deploy.1.gz

%changelog
* Sun Mar 23 2014 Deploy Automated Package Builder - 2.1-43
- rebuilt

* Fri Mar 21 2014 Deploy Automated Package Builder - 2.1-42
- rebuilt

* Fri Mar 21 2014 Deploy Automated Package Builder - 2.1-41
- rebuilt

* Thu Mar 20 2014 Deploy Automated Package Builder - 2.1-40
- rebuilt

* Wed Mar 19 2014 Deploy Automated Package Builder - 2.1-39
- rebuilt

* Tue Mar 18 2014 Deploy Automated Package Builder - 2.1-38
- rebuilt

* Tue Mar 18 2014 Deploy Automated Package Builder - 2.1-37
- rebuilt

* Thu Mar 13 2014 Deploy Automated Package Builder - 2.1-36
- rebuilt

* Thu Mar 13 2014 Deploy Automated Package Builder - 2.1-35
- rebuilt

* Thu Mar 13 2014 Deploy Automated Package Builder - 2.1-34
- rebuilt

* Wed Mar 12 2014 Deploy Automated Package Builder - 2.1-33
- rebuilt

* Tue Mar 11 2014 Deploy Automated Package Builder - 2.1-32
- rebuilt

* Mon Mar 10 2014 Deploy Automated Package Builder - 2.1-31
- rebuilt

* Sat Mar 08 2014 Deploy Automated Package Builder - 2.1-30
- rebuilt

* Sat Mar 08 2014 Deploy Automated Package Builder - 2.1-29
- rebuilt

* Fri Mar 07 2014 Deploy Automated Package Builder - 2.1-28
- rebuilt

* Wed Mar 05 2014 Deploy Automated Package Builder - 2.1-27
- rebuilt

* Wed Mar 05 2014 Deploy Automated Package Builder - 2.1-26
- rebuilt

* Wed Mar 05 2014 Deploy Automated Package Builder - 2.1-25
- rebuilt

* Tue Mar 04 2014 Deploy Automated Package Builder - 2.1-24
- rebuilt

* Tue Mar 04 2014 Deploy Automated Package Builder - 2.1-23
- rebuilt

* Tue Mar 04 2014 Deploy Automated Package Builder - 2.1-22
- rebuilt

* Mon Mar 03 2014 Deploy Automated Package Builder - 2.1-21
- rebuilt

* Mon Mar 03 2014 Deploy Automated Package Builder - 2.1-20
- rebuilt

* Mon Mar 03 2014 Deploy Automated Package Builder - 2.1-19
- rebuilt

* Sun Mar 02 2014 Deploy Automated Package Builder - 2.1-18
- rebuilt

* Sat Mar 01 2014 Deploy Automated Package Builder - 2.1-17
- rebuilt

* Sat Mar 01 2014 Deploy Automated Package Builder - 2.1-16
- rebuilt

* Sat Mar 01 2014 Deploy Automated Package Builder - 2.1-15
- rebuilt

* Sat Mar 01 2014 Deploy Automated Package Builder - 2.1-14
- rebuilt

* Sat Mar 01 2014 Deploy Automated Package Builder - 2.1-13
- rebuilt

* Fri Feb 28 2014 Deploy Automated Package Builder - 2.1-12
- rebuilt

* Fri Feb 28 2014 Deploy Automated Package Builder - 2.1-11
- rebuilt

* Fri Feb 28 2014 Deploy Automated Package Builder - 2.1-10
- rebuilt

* Thu Feb 27 2014 Deploy Automated Package Builder - 2.1-9
- rebuilt

* Wed Feb 26 2014 Deploy Automated Package Builder - 2.1-8
- rebuilt

* Tue Feb 25 2014 Deploy Automated Package Builder - 2.1-7
- rebuilt

* Tue Feb 25 2014 Deploy Automated Package Builder - 2.1-6
- rebuilt

* Thu Feb 20 2014 Deploy Automated Package Builder - 2.1-5
- rebuilt

* Wed Feb 19 2014 Deploy Automated Package Builder - 2.1-4
- rebuilt

* Tue Feb 18 2014 Deploy Automated Package Builder - 2.1-3
- rebuilt

* Sun Feb 16 2014 Deploy Automated Package Builder - 2.1-2
- rebuilt

* Fri Sep 13 2013 Kay Williams <kay@deployproject.org> - 2.1-1
- offline support 
- support for executing deployment scripts from a remote host
- additional templates and template improvements
- robustness and reliability enhancements

* Tue Apr 30 2013 Kay Williams <kay@deployproject.org> - 1.76-1
- gpgkey download and error handling improvements
- add definition-dir macro to srpmbuild/script and update documentation
- add test templates folder and test-web-server-running template
- additional minor error handling improvements

* Thu Apr 18 2013 Kay Williams <kay@deployproject.org> - 1.75-1
- macro and xinclude feature and stability enhancements
- main/id now a required element - avoids unexpected results
- reorganize cache and publish folders to help prevent accidental id clashes
- template and documentation updates

* Sun Mar 10 2013 Kay Williams <kay@deployproject.org> - 1.72-1
- fixed schema folder name that should have been changed in 1.70-1
- improved schema validation for deploy.conf generally
- allow metadata cache folders to move without causing difference events
  Note: this will cause events to run once to update metadata cache schema
- check-kernel.xml template ignores arch when checking latest vs boot kernel

* Wed Feb 27 2013 Kay Williams <kay@deployproject.org> - 1.71-1
- updates to address createrepo datafile naming changes in el6.4
- introducing dnsmasq 2.66.13 to address libvirt changes in el6.4
- minor code variable naming cleanup
- misc documentation updates

* Wed Feb 20 2013 Kay Williams <kay@deployproject.org> - 1.70-1
- using the more general term 'definition' as definition top level element
- updated templates and documentation

* Fri Feb 15 2013 Kay Williams <kay@deployproject.org> - 1.69-1
- added 'main/os' element as a first step toward multi-platform support
- updated templates and documentation

* Mon Dec 17 2012 Kay Williams <kay@deployproject.org> - 1.68-1
- product naming and documentation updates
- fixed bug that was causing config postun scripts to erroneously remove files
- fixed bug that was causing updated deploy scripts to be ignored

* Sat Dec 1 2012 Kay Williams <kay@deployproject.org> - 1.0.61-1
- fix iso install boot arguments for el6; add iso install test case
- add keyboard to ks.cfg (kickstart) template

* Sat Oct 27 2012 Kay Williams <kay@deployproject.org> - 1.0.60-1
- virt-config/virt-install improvements
- product naming and documentation updates

* Mon Oct 15 2012 Kay Williams <kay@deployproject.org> - 1.0.59-1
- product naming and documentation updates

* Wed Sep 26 2012 Kay Williams <kay@deployproject.org> - 1.0.58-1
- documentation updates
- fixed a bug in difference testing for config-rpms that caused rpms to be
  rebuilt in some cases if their relative location in the definition file
  changed
- improved error and uninstall handling for the virt-config.xml template 

* Wed Sep 12 2012 Kay Williams <kay@deployproject.org> - 1.0.57-1
- product naming and documentation updates
- virt-config template flexibility and resilience updates

* Thu Aug 23 2012 Kay Williams <kay@deployproject.org> - 1.0.55-1
- fixes to virt deploy template dependencies
- check-kernel template now more general/robust
- converted config-rpm installdir variable to a macro, which is more generally useful
- updated datfile naming convention for greater stability
- virt-config template starts libvirtd if not running
- updates to documentation and testing to reflect the above

* Wed Aug 15 2012 Kay Williams <kay@deployproject.org> - 1.0.53-1
- improvements to deploy script output; i.e. local scipt output now async
- fixes to virt-deploy.xml, et al., to allow cron execution
- error improvements for missing/unavailable files
- added $installdir convenience variable for config-rpm scripts and triggers
- modified virt-deploy.xml, et al., to create virtual machines using a 'deploy' network, rather than the default virtual network
- modified srpmbuild.xml and deploy.xml to use common virt-install script
- fixed absolute path resolution for srpmbuild templates
- allow macro definitions within text elements, e.g. deploy scripts
- updated documentation and test cases per above

* Mon Jul 30 2012 Kay Williams <kay@deployproject.org> - 1.0.52-1
- Beta 1 Build

* Mon Jul 08 2011 Kay Williams <kay@deployproject.org> - 0.9.1-1
- Initial Build
