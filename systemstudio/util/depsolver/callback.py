#
# Copyright (c) 2010
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
class DepSolverCallback:
  "Simple callback for DepSolver"
  def __init__(self):
    self.loop = 1
  def start(self):
    """
    This method is called once when dependency solving begins.  It
    accepts no arguments.
    """
    print "Starting package resolution..."
  def tscheck(self, unresolved=0):
    """
    This method is called once each loop in dep solving.  Its single
    argument is the number of packages in the unresolved set it is
    checking.
    """
    print "Loop %d: checking %d packages" % (self.loop, unresolved)
  def pkgAdded(self, pkgtup=None, state=None):
    """
    This method is called each time a package is added to the
    transaction set to be checked.  It has two arguments; pkgtup, a
    (n,a,e,v,r) tuple of information about the package, and state, the
    current state of the package.
    """
    print "Added package %s" % (pkgtup[0])
  def run(self):
    """
    This method is called when all the dependencies are resolved and the
    the transaction is run.
    """
    print "Running Transaction"
  def restartLoop(self):
    """
    This method is called each time a single dependency solving loop
    completes.  It accepts no arguments.
    """
    self.loop += 1
  def end(self):
    """
    This method is called once when dependency solving is complete.
    It accepts no arguments.
    """
    print "Package resolution complete"
  def procReq(self):
    pass
  def transactionPopulation(self):
    print "Populating transaction set with selected packages. Please wait."
  def downloadHeader(self, name):
    print "Downloading header for %s to pack into transaction set" % name
  def foundObsolete(self, old, new):
    print "WARNING: %s is now provided by %s" % (old, new)
