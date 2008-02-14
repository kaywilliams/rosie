from distutils.core import setup

import glob
import os

def get_data_files(directory):
    "Return all filenames in directory"
    result = []
    all_results = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            result.append(path)
        else:
            all_results.extend(get_data_files(path))
    if result:
        all_results.append((directory, result))
    return all_results


def get_packages(directory):
    "Return all packages in directory"
    all_results = [directory]
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            all_results.extend(get_packages(path))
    return all_results

setup(name = 'spin',
      version = '1.0',
      description = 'The Spin Package builds customized distributions',
      author = 'Daniel Musgrave',
      author_email = 'dmusgrave@renditionsoftware.com',
      url = 'http://www.renditionsoftware.com/products/spin',
      license = 'GPLv2+',
      packages = get_packages('spin'),
      scripts = ['bin/spin'],
      data_files = get_data_files('share/spin'),
)
