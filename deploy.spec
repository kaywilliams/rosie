%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    deploy
Version: 1.64
Release: 1%{?dist}
Summary: Open platform for managing system and application deployment.

License:   GPL
Group:     Applications/Repo
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
Requires: mkisofs
Requires: openssh 
Requires: pexpect
Requires: pykickstart
Requires: python-crypto
Requires: python-devel
Requires: python-hashlib
Requires: python-lxml
Requires: python-paramiko
Requires: python-setuptools
Requires: rhn-client-tools
Requires: rpm-build
Requires: syslinux
Requires: yum
Requires: xz
Requires: /sbin/rngd

%description
Deploy is an open source, community based platform for managing system and
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
* Wed Dec 12 2012 Kay Williams <kay@deployproject.org> - 1.64.1
- fixed a bug that was causing updated deploy scripts to be ignored

* Tue Dec 11 2012 Kay Williams <kay@deployproject.org> -1.63.1
- product naming and documentation updates
- fixed bug that was causing config postun scripts to erroneously remove files

* Sat Dec 1 2012 Kay Williams <kay@deployproject.org> - 1.0.61.1
- fix iso install boot arguments for el6; add iso install test case
- add keyboard to ks.cfg (kickstart) template

* Sat Oct 27 2012 Kay Williams <kay@deployproject.org> - 1.0.60.1
- virt-config/virt-install improvements
- product naming and documentation updates

* Mon Oct 15 2012 Kay Williams <kay@deployproject.org> - 1.0.59.1
- product naming and documentation updates

* Wed Sep 26 2012 Kay Williams <kay@deployproject.org> - 1.0.58.1
- documentation updates
- fixed a bug in difference testing for config-rpms that caused rpms to be
  rebuilt in some cases if their relative location in the definition file
  changed
- improved error and uninstall handling for the virt-config.xml template 

* Wed Sep 12 2012 Kay Williams <kay@deployproject.org> - 1.0.57.1
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
