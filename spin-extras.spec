%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           spin-extras
Version:        0.8.0
Release:        1%{?dist}
Summary:        The Spin Extras Package.

Group:          Applications/System
License:        GPLv2+
URL:            http://www.renditionsoftware.com/products/spin
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:      noarch

Requires:       spin

%description
The Spin Extras package contains modules that add features to Spin.

%prep
%setup -q

%build

%install
%{__rm} -rf %{buildroot}
%{__make} installextras DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

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

