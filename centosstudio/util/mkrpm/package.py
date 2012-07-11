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
A python module that can be used to read the lead, signature,
header and payload sections of an RPM file.

The signature section that is retrieved by creating an RpmPackage
object can be modified dynamically. Future work on this module
includes being able to modify the header section of the RPM package
programmatically as well.

Most of the ideas in this module are copied from pyrpm with (a few)
minor changes and restructuring of stuff.
"""

__author__ = "Uday Prakash <uprakash@centosstudio.org"
__date__ = "March 30, 2007"
__version__ = "0.1"
__credits__ = "The PyRPM team"

from globals import *

import fcntl
import os
import struct

(pack, unpack) = (struct.pack, struct.unpack)

__all__ = [
  'RpmPackage',
  'toHex',
  ]

def toHex(s):
  lst = []

  for ch in s:
    hv = hex(ord(ch)).replace('0x', '')
    if len(hv) == 1:
      hv = ''.join(['0', hv])
    lst.append(hv)

  return reduce(lambda x,y:x+y, lst)

class RpmPackage:
  """
  The workhorse of this module. Is capable of reading an RPM package
  and allows the calling app dynamically modifying the signature
  section of the RPM file. Future work includes being able to
  dynamically modify the header section as well. Also, currently RPMs
  on the machine are supported; maybe add the functionality to modify
  remote RPMs as well, and make a local copy.
  """

  class HeaderReader:
    """
    A helper for header reading. Should be used in conjunction with
    RpmPackage.
    """

    def __init__(self, tagnames, fd):
      """
      Initialize for reading a header.

      self.tagnames is a dictionary that maps tag IDs to human
      readable names. For example, 1005 maps to 'gpg'.

      self.fd should already be open.
      """
      self.tagnames = tagnames
      self.fd = fd

    def readHeader(self, padding):
      """
      Read the header from the self.fd file object, which is
      currently pointing to the start of the header section in the
      RPM. At the end of the execution of this function's method
      call, the file object is pointing to the end of the header
      section in the RPM.
      """
      header = {}
      items = self.__readIndex(8)
      for i in range(items[0]):
        tag, data = self.__getHeaderByIndex(i, items[3], items[4])
        header[self.tagnames[tag]] = data
      return header

    def __getHeaderByIndex(self, idx, indexdata, storedata):
      """
      Parse value of tag idx.

      Return (tag number, tag data).  Raise ValueError on invalid data.
      """

      index = unpack("!4I", indexdata[idx*16:(idx+1)*16])
      tag = index[0]
      data = self.__parseTag(index, storedata)
      return (tag, data)

    def __parseTag(self, index, fmt):
      """
      Parse value of tag with index from data in fmt.

      Return tag value.  Raise ValueError on invalid data.
      """

      (tag, ttype, offset, count) = index
      try:
        if ttype == RPM_INT32:
          return unpack("!%dI" % count, fmt[offset:offset + count * 4])
        elif ttype == RPM_STRING_ARRAY or ttype == RPM_I18NSTRING:
          data = []
          for _ in xrange(0, count):
            end = fmt.index('\x00', offset)
            data.append(fmt[offset:end])
            offset = end + 1
          return data
        elif ttype == RPM_STRING:
          return fmt[offset:fmt.index('\x00', offset)]
        elif ttype == RPM_CHAR:
          return unpack("!%dc" % count, fmt[offset:offset + count])
        elif ttype == RPM_INT8:
          return unpack("!%dB" % count, fmt[offset:offset + count])
        elif ttype == RPM_INT16:
          return unpack("!%dH" % count, fmt[offset:offset + count * 2])
        elif ttype == RPM_INT64:
          return unpack("!%dQ" % count, fmt[offset:offset + count * 8])
        elif ttype == RPM_BIN:
          return fmt[offset:offset + count]
        raise ValueError, "unknown tag type: %d" % ttype
      except struct.error:
        raise ValueError, "Invalid header data"

    def __readIndex(self, pad):
      """
      Read and verify header index and data.

      self.fd should already be open.  Return (number of tags, tag data size,
      header header, index data, data area, total header size).  Discard data
      to enforce alignment at least pad.  Raise ValueError on invalid data,
      IOError.
      """

      data = self.fd.read(16)
      (magic, indexNo, storeSize) = unpack("!8s2I", data)

      if magic != RPM_HEADER_INDEX_MAGIC or indexNo < 1:
        raise ValueError, "bad index magic"

      indexData = self.fd.read(16*indexNo)
      storeData = self.fd.read(storeSize)

      if pad != 1:
        self.fd.read((pad - (storeSize % pad)) % pad)

      return (indexNo, storeSize, data, indexData, storeData, 16 + len(indexData) + len(storeData))

  ######-----------------End of HeaderReader---------------######

  class HeaderGenerator:
    """
    A helper for header generation. Should be used in conjunction with
    RpmPackage.
    """

    def __init__(self, taghash, tagnames, region):
      """
      Initialize for creating a header with region tag region.

      self.taghash is a dictionary of tuples, each element of which
      is (tag ID, tag datatype, offset, count).

      self.tagnames is a dictionary that maps tag IDs to human
      readable names. For example, 1005 maps to 'gpg'.
      """
      self.taghash = taghash
      self.tagnames = tagnames
      self.region = region
      self.store = ""
      self.offset = 0
      self.indexlist = []

    def outputHeader(self, header, align):
      """
      Return (index data, data area) representing header
      (tag name => tag value), with data area end aligned to align.
      """
      keys = self.tagnames.keys()
      keys.sort()

      #
      # 1st pass: Output sorted non-install-only tags
      #
      for tag in keys:
        #
        # We'll handle the region header at the end.
        #
        if tag == self.region:
          continue
        key = self.tagnames[tag]
        #
        # Skip keys we don't have in the header.
        #
        if header.has_key(key):
          self.__appendTag(tag, header[key])
      #
      # Add region header.
      #
      regiondata = self.__createRegionData()
      self.__appendTag(self.region, regiondata)

      (index, pad) = self.__generateIndex(align)
      return (index, self.store+pad)

    def __appendTag(self, tag, value):
      """Append tag (tag = value)"""
      ttype = self.taghash[tag][1]

      #
      # Convert back the RPM_ARGSTRING to RPM_STRING
      #
      if ttype == RPM_ARGSTRING:
        ttype = RPM_STRING

      (count, data) = self.__generateTag(ttype, value)
      pad = self.__alignTag(ttype)
      self.offset += len(pad)
      self.indexlist.append((tag, ttype, self.offset, count))
      self.store += pad + data
      self.offset += len(data)

    def __createRegionData(self):
      """Return region tag data for current index list."""

      offset = -(len(self.indexlist) * 16) - 16
      #
      # tag, type, offset, count
      #
      return pack("!2IiI", self.region, RPM_BIN, offset, 16)

    def __generateTag(self, ttype, value):
      """
      Return (tag data, tag count for index header) for value of
      ttype.
      """
      #
      # Decide if we have to write out a list or a single element
      #
      if isinstance(value, (tuple, list)):
        count = len(value)
      else:
        count = 0
      #
      # Normally we don't have strings. And strings always need to be
      # '\x00' terminated.
      #
      isstring = 0
      if ttype == RPM_STRING or \
           ttype == RPM_STRING_ARRAY or\
           ttype == RPM_I18NSTRING:
        format = "s"
        isstring = 2
      elif ttype == RPM_BIN:
        format = "s"
      elif ttype == RPM_CHAR:
        format = "!c"
      elif ttype == RPM_INT8:
        format = "!B"
      elif ttype == RPM_INT16:
        format = "!H"
      elif ttype == RPM_INT32:
        format = "!I"
      elif ttype == RPM_INT64:
        format = "!Q"
      else:
        raise NotImplemented, "unknown tag header"
      if count == 0:
        if format == "s":
          data = pack("%ds" % (len(value)+isstring), value)
        else:
          data = pack(format, value)
      else:
        data = ""
        for i in xrange(0,count):
          if format == "s":
            data += pack("%ds" % (len(value[i]) + isstring),
                   value[i])
          else:
            data += pack(format, value[i])
      #
      # Fix counter. If it was a list, keep the counter.
      # If it was a single element, use 1 or if it is a RPM_BIN type the
      # length of the binary data.
      #
      if count == 0:
        if ttype == RPM_BIN:
          count = len(value)
        else:
          count = 1
      return (count, data)

    def __generateIndex(self, pad):
      """
      Return (header tags, padding after data area) with data area end
      aligned to pad.
      """

      index = ""
      for (tag, ttype, offset, count) in self.indexlist:
        #
        # Make sure the region tag is the first one in the index
        # despite being the last in the store
        #
        if tag == self.region:
          index = "".join([pack("!4I", tag, ttype, offset, count),
                   index])
        else:
          index = "".join([index,
                   pack("!4I", tag, ttype, offset, count)])

      align = (pad - (len(self.store) % pad)) % pad
      index = "".join([pack("!8s2I", RPM_HEADER_INDEX_MAGIC,
                  len(self.indexlist),
                  len(self.store) + align),
               index])
      return (index, '\x00' * align)

    def __alignTag(self, ttype):
      """Return alignment data for aligning for ttype from offset
      self.offset."""

      if ttype == RPM_INT16:
        align = (2 - (self.offset % 2)) % 2
      elif ttype == RPM_INT32:
        align = (4 - (self.offset % 4)) % 4
      elif ttype == RPM_INT64:
        align = (8 - (self.offset % 8)) % 8
      else:
        align = 0
      return '\x00' * align

  #####-------------End of HeaderGenerator-------------#####

  def __init__(self, source):
    """
    Initialize variables:
      * self.source: the path to the RPM
      * self.fd: the fd corresponding to self.source
      * self.lead: the lead section of the RPM; use generateLead
      to get ahold of it
      * self.signature: the signature section of the RPM; use
      <object>.signature[item] to modify item's value, and
      generateSignature to generate the signature as a stream of
      bytes.
      * self.header: the header section of the RPM; use
      generateHeader to get ahold of it.
      * self.payload: the payload section of the RPM; use
      generatePayload to get ahold of it.
      * self.headerRange: the range of the header section.
    """
    self.source = source
    self.fd = None
    self.lead = {}
    self.signature = {}
    self.header = None
    self.payload = None
    self.headerRange = (None, None) # start, length
    self.stats = None

  def open(self, mode='r'):
    """
    Open self.source with the mode specified.
    """
    self.stats = os.stat(self.source)
    if not self.fd:
      fd = open(self.source, mode)
      fcntl.fcntl(fd.fileno(), fcntl.F_SETFD, 1)
      self.fd = fd

  def write(self, dest=None):
    """
    Write the file. If dest is None, write to self.source, else
    write to dest.
    """
    if dest:
      self.source = dest
      self.close()
    else:
      self.fd.seek(0)
    self.open('w+')
    lead = self.generateLead()
    (sigindex, sigdata) = self.generateSig()
    header = self.generateHeader()
    payload = self.generatePayload()
    self._write(lead)
    self._write(sigindex)
    self._write(sigdata)
    self._write(header)
    self._write(payload)

  def _write(self, data):
    """
    Private write method.
    """
    if not self.fd:
      self.open('w+')
    self.fd.write(data)

  def close(self, reset=False):
    """
    Close the file. Make sure you call the write() method before
    calling close() if you made changes to any of the data
    structures.

    @param reset: if reset is True, the timestamp of the RPM is
            is set to its original value (when it was opened).
    """
    if self.fd:
      self.fd.close()
      self.fd = None
    os.chmod(self.source, self.stats.st_mode & 07777)
    if reset:
      os.utime(self.source, (self.stats.st_atime, self.stats.st_mtime))

  def read(self):
    """
    Read the RPM and prepare for changes.
    """
    self.open()
    self.readLead()
    self.readSig()
    self.readHeader()
    self.readPayload()

  def isSourceRpm(self):
    """
    Return True if self.source is a source RPM. Uses the lead to
    figure out whether self.source is a source RPM.
    """
    return toHex(self.lead['type']) == '0001'

  def readLead(self):
    """
    Read the lead section of the RPM.
    """
    leaddata = self.fd.read(RPM_LEAD_SIZE)
    if leaddata[:4] != RPM_HEADER_LEAD_MAGIC:
      raise ValueError, "no RPM magic number found"
    self.lead['magic'] = leaddata[0:4]
    self.lead['format'] = leaddata[4:6]
    self.lead['type'] = int(toHex(leaddata[6:8]), 16)
    self.lead['arch'] = int(toHex(leaddata[8:10]), 16)
    self.lead['nevr'] =  leaddata[10:76]
    self.lead['os'] = int(toHex(leaddata[76:78]), 16)
    self.lead['sigtype'] = int(toHex(leaddata[78:80]))

  def generateLead(self):
    """
    Create a byte stream of the lead section which can be used to
    write to a file.
    """
    lead = pack("!4s2c2h66s2h16x",
          RPM_HEADER_LEAD_MAGIC,
          '\x03',
          '\x00',
          self.lead['type'],
          self.lead['arch'],
          self.lead['nevr'],
          self.lead['os'],
          self.lead['sigtype'])
    return lead

  def getLeadRange(self):
    """
    Get the range of the lead section: (start, length).
    """
    return (0, RPM_LEAD_SIZE)

  def readSig(self):
    """
    Read the signature section of the RPM.
    """
    h = self.HeaderReader(rpmsigtagname, self.fd)
    self.signature = h.readHeader(8)

  def generateSig(self):
    """
    Return (index data, data area) representing signature header
    (tag name => tag value).
    """
    h = self.HeaderGenerator(rpmsigtag, rpmsigtagname, 62)
    return h.outputHeader(self.signature, 8)

  def getSignatureRange(self):
    """
    Return the range of the signature section: (start, length).
    """
    (sigindex, sigdata) = self.generateSig()
    length = len(sigindex) + len(sigdata)
    return (RPM_LEAD_SIZE, length)

  def readHeader(self):
    """
    Read the header of the RPM.
    """
    start = self.fd.tell()
    data = self.fd.read(16)
    (magic, indexNo, storeSize) = unpack("!8s2I", data)
    headerBytes = 16 + (indexNo * 16) + storeSize
    self.fd.seek(start)
    self.header = self.fd.read(headerBytes)
    end = self.fd.tell()
    self.headerRange = (start, end)

  def generateHeader(self):
    """
    Return the header of the RPM as a byte stream.
    """
    return self.header

  def getHeaderRange(self):
    """
    Return the range of the header: (start, length).
    """
    return self.headerRange

  def readPayload(self):
    """
    Read the payload of the RPM.
    """
    self.payload = self.fd.read()

  def generatePayload(self):
    """
    Return the payload as a byte stream.
    """
    return self.payload
