#
# Copyright (c) 2011
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
"""

Support for Internationalization (i18n) and Localization (l10n).

This module provides i18n and l10n support using the the GNU gettext 
message catalog library and python's gettext module.

I18n refers to the operation by which a program can be run on machines
with non-English default language settings. L10n refers to the
adapation of the program to the local language and habits.


To localize your module, create an object of the I18n class in this
module (let's call it 'cat' for catalog). Then make method pointers to
the gettext, lgettext and dgetttext methods of the 'cat' object. The
suggested names are _, L_, and D_ respectively. The difference between
these three methods is subtle:

  * gettext: Returns the localized translation of message, based on the
    current global domain, language, and locale directory.

  * lgettext: Equivalent to gettext(), but the translation is returned
    in the preferred system encoding

  * dgettext: Like gettext(), but look the message up in the specified
    domain.

Now that you have nifty pointers all ready to go, set the text domain
of the application. The domain, in this context, refers to the name of
the application. To be more explicit, it is the name of the .mo file
containing the translated strings. You can set the text domain by
cat.setDomain(<domain>).

The last thing, left to be done is to set the languages. This can be
done by cat.setLangs(<list of languages>).

TODO:

  * add support for ngettext
"""

__author__ = "Uday Prakash <uprakash@renditionsoftware.com>"
__date__ = "March 7, 2007"

#
# Shamelessly copied from Anaconda's source tree :)
#

import gzip
import gettext
import locale
import string

class I18n:
    """
    The class whose methods to the actual translation from English
    strings to strings in the local language.
    """
    def __init__(self, domain=None, langs=None, paths=None):
        """
        Initialize variables:
         * self.langs - the languages (a list)
         * self.paths - the list of paths to the locale dirs
           (/usr/share/locale etc.)
         * self.domains = list of domains
         * self.catalogs = dictionary of catalogs (key=domain,
           value=catalog)
        """
        if langs:
            self.langs = langs
        else:
            self.langs = ['C']

        if paths:
            self.paths = paths
        else:
            self.paths = ['/usr/share/locale']

        self.domains = []
        self.catalogs = {}
        self.setDomain(domain)

    def setDomain(self, domain):
        """
        Set the domain to use and then update the cached catalogs to
        make sure all the changes get reflected.
        """
        if type(domain) == type([]):
            domain.reverse()
            for d in domain:
                if d in self.domains:
                    self.domains.pop(self.domains.index(d))
                self.domains.insert(0, d)
        else:
            if domain in self.domains:
                self.domains.pop(self.domains.index(domain))
            self.domains.insert(0, domain)
        self.updateCache()

    def getLangs(self):
        """
        Return the list of languages
        """
        return self.langs

    def setLangs(self, langs):
        """
        Set the list of languages
        """
        self.__init__(domain=self.domains, langs=langs, paths=self.paths)

    def updateCache(self):
        """
        Update the cached catalog objects.
        """
        self.catalogs = {}
        for domain in self.domains:
            mofile = None
            for path in self.paths:
                for lang in self.langs:
                    if domain is None:
                        path = 'po/%s.mo' %lang
                    else:
                        path = '%s/%s/LC_MESSAGES/%s.mo' % (path, lang, domain,)
                    try:
                        f = open(path)
                        buf = f.read(2)
                        f.close()
                        if buf == "\037\213":
                            mofile = gzip.open(path)
                        else:
                            mofile = open(path)
                    except IOError:
                        pass
                    if mofile:
                        break
                if mofile:
                    break
            if mofile:
                catalog = gettext.GNUTranslations(mofile)
                self.catalogs[domain] = catalog

    def gettext(self, string):
        """
        Return the localized translation of message, based on the current
        global domain, language, and locale directory.
        """
        return self.__gettext(string, 'gettext')

    def dgettext(self, domain, string):
        """
        Like gettext(), but look the message up in the specified
        domain.
        """
        if not self.catalog:
            return string
        if self.catalogs.has_key(domain):
            self.catalogs[domain].dgettext(domain, string)
        else:
            return string

    def lgettext(self, string):
        """
        Equivalent to gettext(), but the translation is returned in
        the preferred system encoding, if no other encoding was
        explicitly set with bind_textdomain_codeset().
        """
        return self.__gettext(string, 'lgettext')

    def __gettext(self, string, id):
        if len(self.catalogs) == 0:
            return string
        for domain in self.domains:
            if not self.catalogs.has_key(domain):
                continue
            translation = {
                'lgettext': self.catalogs[domain].lgettext,
                'gettext': self.catalogs[domain].gettext,}[id](string)
            if translation:
                return translation
        return string

def expandLangs(astring):
    langs = [astring]
    charset = None
    # remove charset
    if '.' in astring:
        langs.append(string.split(astring, '.')[0])
    if '@' in astring:
        charset = string.split(astring, '@')[1]
    # also add 2 character language code
    if len(astring) > 2:
        if charset: langs.append("%s@%s" %(astring[:2], charset))
        langs.append(astring[:2])

    return langs

def N_(str):
    return str

"""
cat = I18n()
_ = cat.gettext
L_ = cat.lgettext
D_ = cat.dgettext

Set Text Domain:
 cat.setDomain(domain)

Set Languages:
 cat.setLangs(langs)
"""
