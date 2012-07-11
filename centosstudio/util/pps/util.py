#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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
"""
util.py - various utility functions
"""

SUPPORTED_SCHEMES = ['ftp', 'http', 'https', 'file', 'rhn', 'rhns'] #!

#------ URL PATH PROCESSING ------#
def urlunparse((scheme, netloc, url, params, query, fragment)):
  if params:   url = '%s;%s' % (url, params)
  if netloc or (scheme and url[:2] != '//'):
    if url and not url.startswith('/'):
      url = '/' + url
    url = '//%s%s' % (netloc or '', url)
  if scheme:   url = '%s:%s' % (scheme, url)
  if query:    url = '%s?%s' % (url, query)
  if fragment: url = '%s#%s' % (url, fragment)
  return url

def urlparse(url):
  url = str(url) # stop the crazy Path proliferation!
  scheme = netloc = params = query = fragment = ''
  i = url.find(':')
  if i > 0:
    if url[:i].lower() in SUPPORTED_SCHEMES:
      scheme, url = url[:i].lower(), url[i+1:]
  if url[:2] == '//':
    netloc, url = _splitnetloc(url, 2)
  if not (scheme == '' or scheme == 'file'):
    if '#' in url:
      url, fragment = url.split('#', 1)
    if '?' in url:
      url, query    = url.split('?', 1)
    if ';' in url:
      url, params   = url.split(';', 1)
  return (scheme, netloc, url or '/', params, query, fragment)

def _splitnetloc(url, start=0):
  for c in '/?#': # order matters
    delim = url.find(c, start)
    if delim >= 0:
      break
  else:
    delim = len(url)
  return url[start:delim], url[delim:]

def _normpart(part):
  if not part: return
  return '&'.join(sorted(part.split('&')))
