#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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
import rpmUtils.transaction
import rpm

REPLACEMENT_VARS = {
  '%{name}': 'name',
  '%{version}': 'version',
  '%{release}': 'release',
  #${<replacement string>}: <rpm header var name>
}

def requires(req, installroot='/', fmt="%{name}-%{version}-%{release}"):
  """
  requires = requires(req[,installroot,fmt])

  Compute what packages have the requirement req.  If installroot is set,
  use a different install root than /.  Results are returned in a list
  of strings formatted according to fmt.  Current available macros for
  expansion are listed in REPLACEMENT_VARS, above.
  """
  ts = rpmUtils.transaction.initReadOnlyTransaction(root=installroot)
  ts.pushVSFlags(~(rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS))
  idx = ts.dbMatch('provides', req)
  if idx.count() == 0:
    ret = None
  else:
    ret = fmt
    hdr = idx.next()
    # perhaps a smarter way to do this would be to find the vars that
    # need replacing and to replace only them via lookup (esp. if the
    # replacement table gets overly large)
    for k,v in REPLACEMENT_VARS.items():
      ret = ret.replace(k,hdr[v])
    del hdr
  del idx
  del ts
  return ret
