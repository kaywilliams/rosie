%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    centosstudio
Version: 1.35
Release: 1%{?dist}
Summary: Platform for delivering CentOS and RHEL-based systems and applications

License:   GPL
Group:     Applications/System
URL:       http://www.centossolutions.com/centosstudio
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

BuildRequires: docbook-style-xsl
# xml and sgml catalogs needed by docbook-style-xsl 
BuildRequires: /etc/xml/catalog
BuildRequires: /etc/sgml/catalog
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
CentOS Studio is a complete platform to automate build, test, deployment
and maintenance for systems and applications based on  CentOS and Red Hat
Enterprise Linux. See http://www.centossolutions.com for more information. 

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
%config(noreplace) %{_sysconfdir}/logrotate.d/centosstudio
%{python_sitelib}/*
%{_bindir}/centosstudio
%{_datadir}/centosstudio
%doc COPYING
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/centosstudio.conf.5.gz
%{_mandir}/man1/centosstudio.1.gz

%changelog
* Wed Apr 25 2012 Kay Williams <kay@centossolutions.com> - 1.0.35-1
- Beta 1 Build

* Mon Jul 08 2011 Kay Williams <kay@centossolutions.com> - 0.9.1-1
- Initial Build
