#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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
#------ ERRORS ------#
class ImageIOError(StandardError):
  "Class of errors raised when an IO error happens with an image"

# I dunno if I want to keep these or not...
ERROR_GETSIZE        = 'Cannot compute image size: %s'
ERROR_GETCAPACITY    = 'Cannot compute image capacity: %s'
ERROR_ALREADY_OPEN   = 'Image is already open'
ERROR_ALREADY_CLOSED = 'Image is already closed'
ERROR_FLUSH  = 'Error running flush(): %s'
ERROR_WRITE  = 'Error writing: %s'
ERROR_COPY   = 'Error copying: %s'
ERROR_REMOVE = 'Error removing: %s'
ERROR_NOT_ZIPPED = 'Image not zipped'
ERROR_ZIPPED     = 'Image already zipped'
ERROR_LIST = 'Error listing: %s'
