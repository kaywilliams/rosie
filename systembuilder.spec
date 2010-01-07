%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    systembuilder
Version: 1.8.0
Release: 1%{?dist}
Summary: Builds system distributions based on CentOS and Red Hat Enterprise Linux

License:   GPLv2+
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
Requires: netpbm-progs
Requires: python-devel
Requires: python-imaging
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: rhn-client-tools
Requires: rpm-build
Requires: syslinux
Requires: yum

%description
SystemBuilder is an industry best practice solution for deploying
and maintaining Centos and Red Hat Enterprise Linux systems
in physical, virtual and cloud environments. See 
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
%doc docsrc/images*
%{_mandir}/man5/systembuilder.conf.5.gz
%{_mandir}/man1/systembuilder.1.gz

%changelog

* Thu Jan 07 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.2
- merged systembuilder and systembuilder-enterprise rpms

* Thu Dec 10 2009 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- Initial Build
