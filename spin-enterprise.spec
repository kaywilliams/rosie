%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           spin-enterprise
Version:        0.8.0
Release:        1%{?dist}
Summary:        The Spin Enterprise Package

Group:          Applications/System
License:        GPLv2+
URL:            http://www.renditionsoftware.com/products/spin
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:      noarch

Requires:       spin

%description
The Spin Enterprise package contains modules that adds the logos-rpm
event to Spin.  It also requires rhnlib and rhn-client-tools so that
RHN paths can be used in baseurls of repositories.

%prep
%setup -q

%build

%install
%{__rm} -rf %{buildroot}
%{__make} install-enterprise DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm*
%doc COPYING
%doc AUTHORS

%changelog
* Thu Oct  9 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.8.0-1
- Initial Build. (uprakash)

