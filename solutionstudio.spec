%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    solutionstudio
Version: 0.9
Release: 1%{?dist}
Summary: Builds system distributions based on CentOS and Red Hat Enterprise Linux

License:   GPL
Group:     Applications/System
URL:       http://www.renditionsoftware.com/solutionstudio
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
Requires: python-devel
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: rhn-client-tools
Requires: rpm-build
Requires: yum

%description
SolutionStudio is an industry best practice solution for deploying
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
%config(noreplace) %{_sysconfdir}/logrotate.d/solutionstudio
%{python_sitelib}/*
%{_bindir}/solutionstudio
%{_datadir}/solutionstudio
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/solutionstudio.conf.5.gz
%{_mandir}/man1/solutionstudio.1.gz

%changelog
* Fri Mar 26 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.5-1
- depsolve changes to avoid pulling in unnecessary packages

* Wed Feb 24 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.4-1
- bumped config module version

* Wed Feb 24 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.3-1
- fixed yum-sync plugin command registration

* Mon Feb 22 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.2-1
- added yum-sync plugin
- renamed config-rpm module to config
- modified config schema
- modified packages to include only mandatory and default group packages

* Thu Jan 07 2010 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- merged solutionstudio and solutionstudio-enterprise rpms

* Thu Dec 10 2009 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- Initial Build
