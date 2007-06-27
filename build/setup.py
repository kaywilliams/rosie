from distutils.core import setup
from ConfigParser import ConfigParser, NoOptionError
from distutils.command.bdist_rpm import bdist_rpm as _bdist_rpm
from distutils.command.install import install as _install

import re

config = ConfigParser()
config.read('setup.cfg')

class Parser:
    
    required = ['name', 'version', 'long_description', 'description',
                'license', 'author', 'author_email', 'url']
    optional = ['maintainer', 'maintainer_email', 'package_dir',
                'packages', 'scripts', 'py_modules', 'package_data',
                'data_files', 'classifiers']
    
    package_section = 'pkg_data'
    
    def __init__(self):
        if not config.has_section(self.package_section):
            raise RuntimeError("pkg_data section with the name, version etc. not found")
        
    def parse(self):
        attrs = {
            'cmdclass': {
                'bdist_rpm': bdist_rpm,
                'install': install,
            }
        }
        
        for option in self.required:
            value = self._get_value(option, required=True)
            attrs[option] = value
        for option in self.optional:
            value = self._get_value(option, required=False)
            if value:
                attrs[option] = value
        return attrs
    
    def _get_value(self, option, required=False):
        try:            
            value = config.get(self.package_section, option)
            formatter = '_format_%s' %(option,)
            if hasattr(self, formatter):
                method = getattr(self, formatter)
                return method(value.strip())
            else:
                return value            
        except NoOptionError:
            if required:
                raise
            else:
                return None

    def _format_long_description(self, value, width=70):
        # if there are any new lines in the long description, it is
        # assumed that the writer went through the trouble of making
        # sure that there are at most 80 characters in a
        # line. Otherwise, the line is split at @param.width
        # characters and returned.        
        if value.find('\n') != -1:
            return value
        else:
            import math
            lines = [ value[width*i:width*(i+1)] \
                      for i in xrange(int(math.ceil(1.*len(value)/width))) ]
            return '\n'.join(lines)
    
    def _format_data_files(self, value):        
        return self._format_as_dict(value, multiple=True, aslist=True)
    
    def _format_package_data(self, value):
        return self._format_as_dict(value, multiple=True)

    def _format_classifiers(self, value):
        return self._format_as_list(value, delim='\n')

    def _format_as_list(self, value, delim=None):
        if delim:
            return [x.strip() for x in value.split(delim)]
        else:
            return [x.strip() for x in value.split()]

    def _format_as_dict(self, value, multiple=False, aslist=False):
        """
        If aslist if False, a dictionary is returned. If aslist if True
        a list is returned; every element of the list is a 2-tuple, the
        first entry of the tuple is the key in the dictionary created
        and the second entry is the value of the dictionary created.
        """
        rtn = {}
        if multiple:
            pattern = ' *[^\:, \n]+ *:(?: *[^\:, \n ]+ *,)* *[^:, \n]+[ |\n]*'
        else:
            pattern = ' *[^:, \n]+ *: *[^\:, \n]+[ |\n]*'
        regex = re.compile(pattern)
        items = [x.strip() for x in regex.findall(value)]
        for item in items:
            tokens = item.split(':')
            if multiple:
                rtn[tokens[0].strip()] = [x.strip() for x in tokens[1].strip().split(',')]
            else:
                rtn[tokens[0].strip()] = tokens[1].strip()
        if aslist:
            return rtn.items()
        return rtn

    _format_package_dir = _format_as_dict
    _format_packages = _format_scripts = _format_py_modules = _format_as_list

class bdist_rpm(_bdist_rpm):
    _bdist_rpm.user_options.extend([
        ('config-files=', None, "files that will be added as configuration files"),
        ('doc-dirs=', None, "directories to be added as documentation directories"),
    ])
    
    def initialize_options(self):
        _bdist_rpm.initialize_options(self)
        self.config_files = None
        self.doc_dirs = None

    def finalize_options(self):
        _bdist_rpm.finalize_options(self)
        self.ensure_string_list('config_files')
        self.ensure_string_list('doc_dirs')

    def _make_spec_file(self):
        f = _bdist_rpm._make_spec_file(self)

        # fix prefix redundancy
        self.__update(f, 'Prefix', replacement=None)

        # fix BuildRoot tag
        self.__update(f, 'BuildRoot',
                      'BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)')
        
        # get rid of vendor tag
        self.__update(f, 'Vendor', replacement=None)

        # make setup quiet
        self.__update(f, '%setup', replacement='%setup -q')
        
        # make sure that the first thing done in the %install section is
        # cleaning out the RPM_BUILD_ROOT
        idx = f.index('%install')
        if f[idx+1] != 'rm -rf $RPM_BUILD_ROOT':
            f.insert(idx+1, 'rm -rf $RPM_BUILD_ROOT')

        # set up the %config files
        if self.config_files:
            self.__modify_section(f, '%files', '%config(noreplace)', self.config_files, offset=2)

        # distutils adds all the doc files on one line, rpmbuild
        # fails on it. If there are more than one doc files
        # specified, break them up into individual lines.        
        if self.doc_files and len(self.doc_files) > 1:
            self.__modify_section(f, '%doc', '%doc', self.doc_files, remove=True)

        if self.doc_dirs:
            self.__modify_section(f, '%files', '%docdir', self.doc_dirs, offset=2)
        
        return f
                                 
    def __update(self, specfile, id, replacement=None):
        present = False
        for i,x in enumerate(specfile):
            if x.startswith(id): present = True; break
            
        if present:
            specfile.pop(i)
            if replacement is not None: specfile.insert(i, replacement)
    
    def __modify_section(self, specfile, tag, descriptive, value, remove=False, offset=0):
        for i,l in enumerate(specfile):
            if l.startswith(tag): break
        if remove: specfile.pop(i)
        i += offset        
        for x in value:
            specfile.insert(i, ''.join([descriptive, ' ', x]))

#            
# A bug in distutils causes rpmbuild to fail
# if optimize is set to False. This class takes care of that.
# If this fix is not there, rpmbuild dies.
#
class install(_install):
    def initialize_options(self):
        _install.initialize_options(self)
        self.optimize = True

def main():
    p = Parser()
    attrs = p.parse()
    setup(**attrs)

if __name__ == "__main__":
    main()
