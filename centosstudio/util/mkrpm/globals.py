#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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
Copied from pyrpm's source tree.

Our additions:
 1. RPM_LEAD_SIZE
"""

__author__  = 'Uday Prakash <uprakash@centosstudio.org>'
__date__    = 'March 30, 2007'
__credits__ = 'The PyRPM Team'

#
# The size of the lead section of an RPM
#
RPM_LEAD_SIZE = 96

#
# RPM Constants - based from rpmlib.h and elsewhere
#

#
# RPM tag types
#
RPM_NULL = 0
RPM_CHAR = 1
RPM_INT8 = 2
RPM_INT16 = 3
RPM_INT32 = 4
RPM_INT64 = 5 # currently unused
RPM_STRING = 6
RPM_BIN = 7
RPM_STRING_ARRAY = 8
RPM_I18NSTRING = 9
RPM_ARGSTRING = 12

#
# RPM Tag elements. Not used currently.
#
rpmtag = {
  # basic info
  "name": (1000, RPM_STRING, None, 0),
  "epoch": (1003, RPM_INT32, 1, 0),
  "version": (1001, RPM_STRING, None, 0),
  "release": (1002, RPM_STRING, None, 0),
  "arch": (1022, RPM_STRING, None, 0),

  # dependencies: provides, requires, obsoletes, conflicts
  "providename": (1047, RPM_STRING_ARRAY, None, 0),
  "provideflags": (1112, RPM_INT32, None, 0),
  "provideversion": (1113, RPM_STRING_ARRAY, None, 0),
  "requirename": (1049, RPM_STRING_ARRAY, None, 0),
  "requireflags": (1048, RPM_INT32, None, 0),
  "requireversion": (1050, RPM_STRING_ARRAY, None, 0),
  "obsoletename": (1090, RPM_STRING_ARRAY, None, 4),
  "obsoleteflags": (1114, RPM_INT32, None, 4),
  "obsoleteversion": (1115, RPM_STRING_ARRAY, None, 4),
  "conflictname": (1054, RPM_STRING_ARRAY, None, 0),
  "conflictflags": (1053, RPM_INT32, None, 0),
  "conflictversion": (1055, RPM_STRING_ARRAY, None, 0),

  # triggers
  "triggername": (1066, RPM_STRING_ARRAY, None, 4),
  "triggerflags": (1068, RPM_INT32, None, 4),
  "triggerversion": (1067, RPM_STRING_ARRAY, None, 4),
  "triggerscripts": (1065, RPM_STRING_ARRAY, None, 4),
  "triggerscriptprog": (1092, RPM_STRING_ARRAY, None, 4),
  "triggerindex": (1069, RPM_INT32, None, 4),

  # scripts
  "prein": (1023, RPM_STRING, None, 4),
  "preinprog": (1085, RPM_ARGSTRING, None, 4),
  "postin": (1024, RPM_STRING, None, 4),
  "postinprog": (1086, RPM_ARGSTRING, None, 4),
  "preun": (1025, RPM_STRING, None, 4),
  "preunprog": (1087, RPM_ARGSTRING, None, 4),
  "postun": (1026, RPM_STRING, None, 4),
  "postunprog": (1088, RPM_ARGSTRING, None, 4),
  "verifyscript": (1079, RPM_STRING, None, 4),
  "verifyscriptprog": (1091, RPM_ARGSTRING, None, 4),

  # addon information:
  "i18ntable": (100, RPM_STRING_ARRAY, None, 0), # list of available langs
  "summary": (1004, RPM_I18NSTRING, None, 0),
  "description": (1005, RPM_I18NSTRING, None, 0),
  "url": (1020, RPM_STRING, None, 0),
  "license": (1014, RPM_STRING, None, 0),
  "rpmversion": (1064, RPM_STRING, None, 0),
  "sourcerpm": (1044, RPM_STRING, None, 4),
  "changelogtime": (1080, RPM_INT32, None, 0),
  "changelogname": (1081, RPM_STRING_ARRAY, None, 0),
  "changelogtext": (1082, RPM_STRING_ARRAY, None, 0),
  "prefixes": (1098, RPM_STRING_ARRAY, None, 4),   # relocatable rpm packages
  "optflags": (1122, RPM_STRING, None, 4),         # optimization flags for gcc
  "pubkeys": (266, RPM_STRING_ARRAY, None, 4),
  "sourcepkgid": (1146, RPM_BIN, 16, 4),           # md5 from srpm (header+payload)
  "immutable": (63, RPM_BIN, 16, 0),               # IIiI: tag, type, -(nr_idx-1)*16, 16
  "image": (61, RPM_BIN, 16, 0),                   # IIiI: tag, type, -(nr_idx-1)*16, 16
  # less important information:
  "buildtime": (1006, RPM_INT32, 1, 0),            # time of rpm build
  "buildhost": (1007, RPM_STRING, None, 0),        # hostname where rpm was built
  "cookie": (1094, RPM_STRING, None, 0),           # build host and time
  # ignored now, successor is comps.xml
  # Code allows hardcoded exception to also have type RPM_STRING
  # for RPMTAG_GROUP==1016.
  "group": (1016, RPM_I18NSTRING, None, 0),
  "size": (1009, RPM_INT32, 1, 0),                 # sum of all file sizes
  "distribution": (1010, RPM_STRING, None, 0),
  "vendor": (1011, RPM_STRING, None, 0),
  "packager": (1015, RPM_STRING, None, 0),
  "os": (1021, RPM_STRING, None, 0),               # always "linux"
  "payloadformat": (1124, RPM_STRING, None, 0),    # "cpio"
  "payloadcompressor": (1125, RPM_STRING, None, 0),# "gzip" or "bzip2"
  "payloadflags": (1126, RPM_STRING, None, 0),     # "9"
  "rhnplatform": (1131, RPM_STRING, None, 4),      # == arch
  "platform": (1132, RPM_STRING, None, 0),

  # rpm source packages:
  "source": (1018, RPM_STRING_ARRAY, None, 2),
  "patch": (1019, RPM_STRING_ARRAY, None, 2),
  "buildarchs": (1089, RPM_STRING_ARRAY, None, 2),
  "excludearch": (1059, RPM_STRING_ARRAY, None, 2),
  "exclusivearch": (1061, RPM_STRING_ARRAY, None, 2),
  "exclusiveos": (1062, RPM_STRING_ARRAY, None, 2), # ['Linux'] or ['linux']

  # information about files
  "dirindexes": (1116, RPM_INT32, None, 0),
  "dirnames": (1118, RPM_STRING_ARRAY, None, 0),
  "basenames": (1117, RPM_STRING_ARRAY, None, 0),
  "fileusername": (1039, RPM_STRING_ARRAY, None, 0),
  "filegroupname": (1040, RPM_STRING_ARRAY, None, 0),
  "filemodes": (1030, RPM_INT16, None, 0),
  "filemtimes": (1034, RPM_INT32, None, 0),
  "filedevices": (1095, RPM_INT32, None, 0),
  "fileinodes": (1096, RPM_INT32, None, 0),
  "filesizes": (1028, RPM_INT32, None, 0),
  "filemd5s": (1035, RPM_STRING_ARRAY, None, 0),
  "filerdevs": (1033, RPM_INT16, None, 0),
  "filelinktos": (1036, RPM_STRING_ARRAY, None, 0),
  "fileflags": (1037, RPM_INT32, None, 0),
  "fileverifyflags": (1045, RPM_INT32, None, 0),
  "fileclass": (1141, RPM_INT32, None, 0),
  "filelangs": (1097, RPM_STRING_ARRAY, None, 0),
  "filecolors": (1140, RPM_INT32, None, 0),
  "filedependsx": (1143, RPM_INT32, None, 0),
  "filedependsn": (1144, RPM_INT32, None, 0),
  "classdict": (1142, RPM_STRING_ARRAY, None, 0),
  "dependsdict": (1145, RPM_INT32, None, 0),

  # SELinux stuff, needed for some FC4-extras packages
  "policies": (1150, RPM_STRING_ARRAY, None, 0),

  # tags not in Fedora Core development trees anymore:
  "filecontexts": (1147, RPM_STRING_ARRAY, None, 1), # selinux filecontexts
  "capability": (1105, RPM_INT32, None, 1),
  "xpm": (1013, RPM_BIN, None, 1),
  "gif": (1012, RPM_BIN, None, 1),
  # bogus RHL5.2 data in XFree86-libs, ash, pdksh
  "verifyscript2": (15, RPM_STRING, None, 1),
  "nosource": (1051, RPM_INT32, None, 1),
  "nopatch": (1052, RPM_INT32, None, 1),
  "disturl": (1123, RPM_STRING, None, 1),
  "oldfilenames": (1027, RPM_STRING_ARRAY, None, 1),
  "triggerin": (1100, RPM_STRING, None, 5),
  "triggerun": (1101, RPM_STRING, None, 5),
  "triggerpostun": (1102, RPM_STRING, None, 5),

  # install information
  "install_size_in_sig": (257, RPM_INT32, 1, 0),
  "install_md5": (261, RPM_BIN, 16, 0),
  "install_gpg": (262, RPM_BIN, None, 0),
  "install_badsha1_1": (264, RPM_STRING, None, 1),
  "install_badsha1_2": (265, RPM_STRING, None, 1),
  "install_dsaheader": (267, RPM_BIN, 16, 0),
  "install_sha1header": (269, RPM_STRING, None, 0),
  "installtime": (1008, RPM_INT32, None, 0),
  "filestates": (1029, RPM_CHAR, None, 0),
  "archivesize": (1046, RPM_INT32, 1, 1),
  "instprefixes": (1099, RPM_STRING_ARRAY, None, 0),
  "installcolor": (1127, RPM_INT32, None, 0),
  "installtid": (1128, RPM_INT32, None, 0)
}

rpmtagname = {}
# Add a reverse mapping for all tags and a new tag -> name mapping.
for key in rpmtag.keys():
  v = rpmtag[key]
  rpmtag[v[0]] = v
  rpmtagname[v[0]] = key
del v
del key

# Required tags in a header.
rpmtagrequired = []
for key in ["name", "version", "release", "arch"]:
  rpmtagrequired.append(rpmtag[key][0])
del key

# Info within the sig header.
rpmsigtag = {
  # size of gpg/dsaheader sums differ between 64/65(contains '\n')
  "dsaheader": (267, RPM_BIN, None, 0),
  "rsaheader": (268, RPM_BIN, None, 0),
  "sha1header": (269, RPM_STRING, None, 0),
  "longsigsize": (270, RPM_INT64, None, 0),
  "longarchivesize": (271, RPM_INT64, None, 0),
  "gpg": (1005, RPM_BIN, None, 0),
  "header_signatures": (62, RPM_BIN, 16, 0), # content of this tag is unclear
  "payloadsize": (1007, RPM_INT32, 1, 0),
  "size_in_signature": (1000, RPM_INT32, 1, 0),
  "md5": (1004, RPM_BIN, 16, 0),
  # legacy entries in older rpm packages:
  "pgp": (1002, RPM_BIN, None, 1),
  "badsha1_1": (264, RPM_STRING, None, 1),
  "badsha1_2": (265, RPM_STRING, None, 1)
}

#
# Add a reverse mapping for all tags and a new tag -> name mapping
#
rpmsigtagname = {}
for key in rpmsigtag.keys():
  v = rpmsigtag[key]
  rpmsigtag[v[0]] = v
  rpmsigtagname[v[0]] = key
del key
del v

#
# Required tags in a signature header.
#
rpmsigtagrequired = []
for key in ["md5"]:
  rpmsigtagrequired.append(rpmsigtag[key][0])
del key

#
# Some special magics for binary rpms
#
RPM_HEADER_LEAD_MAGIC = '\xed\xab\xee\xdb'
RPM_HEADER_INDEX_MAGIC = "\x8e\xad\xe8\x01\x00\x00\x00\x00"
