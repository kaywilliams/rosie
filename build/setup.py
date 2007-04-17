from distutils.core import setup
from ConfigParser import ConfigParser, NoOptionError
from distutils.command.bdist_rpm import bdist_rpm as _bdist_rpm
from distutils.command.install import install as _install

config = ConfigParser()
config.read('setup.cfg')

class bdist_rpm(_bdist_rpm):
    def initialize_options(self):
        _bdist_rpm.initialize_options(self)
        try:
            self.config_files = config.get('bdist_rpm', 'config_files')
        except NoOptionError:
            self.config_files = None

    def _make_spec_file(self):
        f = _bdist_rpm._make_spec_file(self)
        if self.config_files:
            for cf in self.config_files.split():
                f.append("%%config %s" % (cf,))
        return f

#            
# A bug in distutils causes rpmbuild to fail
# if optimize is set to False. This class takes care of that.
# This causes rpmbuild to die.
#
class install(_install):
    def initialize_options(self):
        _install.initialize_options(self)
        self.optimize = True

def getValue(key):
    return config.get('pkg_data', key)

def main():
    global config
    if not config.has_section('pkg_data'):
        #
        # This is bad for us, because now we don't have the name of the RPM
        # in the setup.cfg :(
        #
        del config
        raise RuntimeError, "pkg_data section with the name, version etc. not found"

    name = getValue('name')
    version = getValue('version')
    long_description = getValue('long_description')
    description = getValue('description')
    license = getValue('license')
    author = getValue('author')
    author_email = getValue('author_email')
    url = getValue('url')
    
    setup(name=name,
          version=version,
          description=description,
          long_description=long_description,
          license=license,
          author=author,
          author_email=author_email,
          url=url,
          package_dir={'dimsbuild':'lib',
                       'dimsbuild.plugins': 'lib/plugins'},
          packages=['dimsbuild', 'dimsbuild.plugins'],
          scripts=['bin/dimsbuild'],
          cmdclass={'bdist_rpm': bdist_rpm,
                    'install': install,}          
          )
    
if __name__ == "__main__":
    main()
