%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           systembuilder-enterprise
Version:        1.0.0
Release:        1%{?dist}
Summary:        Provides additional SystemBuilder features

Group:          Applications/System
License:        GPLv2+
URL:            http://www.renditionsoftware.com/SystemBuilder
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:      noarch

BuildRequires:  python

Requires:       rhn-client-tools
Requires:       systembuilder
Requires:       systembuilder-logos

%description
The SystemBuilder Enterprise package provides additional features for
SystemBuilder. It also allows connecting directly to Red Hat Network as an
input source for distribution packages.

%prep
%setup -q

%build

%install
%{__rm} -rf %{buildroot}
%{__make} --makefile Makefile.enterprise install DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/systembuilder/modules/core/rpmbuild/logos-rpm*
%doc COPYING
%doc AUTHORS

%changelog
* Fri Nov 07 2008 Uday Prakash <uprakash@renditionsoftware.com> - 1.0.0-1
- Bumped to 1.0. (uprakash)

* Mon Oct 20 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.9.2-1
- Updated the description and summary of the RPM. (kwilliams)

* Thu Oct 16 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.9.1-1
- Initial Build

