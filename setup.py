#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from distutils.core import setup

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
      version = '0.8.34',
      description = 'The Spin Package builds customized distributions',
      author = 'Daniel Musgrave',
      author_email = 'dmusgrave@renditionsoftware.com',
      url = 'http://www.renditionsoftware.com/products/spin',
      license = 'GPLv2+',
      packages = get_packages('spin'),
      scripts = ['bin/spin'],
      data_files = get_data_files('share/spin'),
)
