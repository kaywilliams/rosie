#
# Copyright (c) 2012
# Deploy Foundation. All rights reserved.
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
import yum

from depsolver import Depsolver, DeployYum
from callback  import DepSolverCallback

def resolve(packages=None, required=None, config='/etc/yum.conf',
            root='/tmp/depsolver', arch='i686', callback=None):
  """
  [ (n,a,e,v,r), (n,a,e,v,r), ... ] = resolve(packages, groups[, ...])

  Resolve dependencies of all specified packages, returning a list of
  package tuples (name, architecture, epoch, version, release).

  The optional root parameter determines where metadata will be stored
  and where dependencies are calculated from; setting this to '/'
  typicaly has the effect of checking dependencies against whatever is
  already installed on the system.  Setting root to some consistent
  location will make subsequent executions of resolve() considerably
  faster, as the metadata will not have to be regenerated each time.

  The optional logger parameter allows you to specify a logger-type
  object to use for printing information and errors.  Logger instances
  must have a threshold argument to their __init__() method and must
  support the log(level, msg) method.  If one is not specified, the
  default yum logger is used with a threshold of -1 (which doesn't
  print anything).
  """
  required = required or []
  solver = Depsolver(config=config, root=root, arch=arch, callback=callback)

  solver.setup()

  if packages is not None:
    if not hasattr(packages, '__iter__'): packages = [packages]
    for package in packages:
      try:
        solver.install(name=package)
      except yum.Errors.InstallError:
        if package in required:
          raise yum.Errors.InstallError("cannot find match for package '%s'" % package)
        else:
          solver.logger.warning("Warning: cannot find match for package '%s'" % package)

  # resolve dependencies
  pos = solver.getPackageObjects()
  ret = [ po.pkgtup for po in pos ]
  solver.teardown()

  return ret
