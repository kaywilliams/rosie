%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    systembuilder
Version: 1.0.3
Release: 1%{?dist}
Summary: Builds system distributions based on CentOS and Red Hat Enterprise Linux

License:   GPL
Group:     Applications/System
URL:       http://www.renditionsoftware.com/systembuilder
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
Requires: mkisofs
Requires: python-devel
Requires: python-hashlib
Requires: python-lxml
Requires: python-setuptools
Requires: rhn-client-tools
Requires: rpm-build
Requires: syslinux
Requires: yum

%description
SystemBuilder builds complete, self-contained system distributions 
based on CentOS and Red Hat Enterprise Linux. See 
http://www.renditionsoftware.com for more information. 

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
%config(noreplace) %{_sysconfdir}/logrotate.d/systembuilder
%{python_sitelib}/*
%{_bindir}/systembuilder
%{_datadir}/systembuilder
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/systembuilder.conf.5.gz
%{_mandir}/man1/systembuilder.1.gz

%changelog
* Mon Dec 06 2010 Kay Williams <kayw@systembuilder.org> - 1.0.3-1
- added installclass for anaconda rhel6 (kayw)
- changed name of rpmbuild-repo to  repo (kayw)
- updates-image and product-image no longer look for existing images (kayw)
- changed default sbtest distro to centos 5 (kayw)
- removed support for xen-images (kayw)
- rendition software naming (kayw)
- modified gpgsign to verify supplied passphrase, difftest config (kayw)
- hashlib fixes (kayw)
- added support for sha256 (kayw)
- added 'Red Hat Enterprise Linux' entry to yum_plugin locals file (kayw)
- removing conditional packages from pkglist - implementation was broken - consider adding back later (kayw)
- config: postun cleans empty dirs only if files folder exists (kayw)

* Sat Jun 05 2010 Kay Williams <kwilliams@renditionsoftware.com> - 1.0.2-1
- config: postun cleans empty dirs only if files folder exists 

* Thu Jun 03 2010 Kay Williams <kwilliams@renditionsoftware.com> - 1.0-1

* Tue Jun 01 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.9.1-1
- Initial Build
