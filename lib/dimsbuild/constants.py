import re

BOOLEANS_TRUE  = ['True', 'true', 'Yes', 'yes', 'On', 'on', '1']
BOOLEANS_FALSE = ['False', 'false', 'No', 'no', 'Off', 'off', '0']

RPM_GLOB  = '*.[Rr][Pp][Mm]'
SRPM_GLOB = '*.[Ss][Rr][Cc].[Rr][Pp][Mm]'

RPM_REGEX  = re.compile('.*\.[Rr][Pp][Mm]')
SRPM_REGEX = re.compile('.*\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]')

RPM_PNVRA_REGEX  = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Rr][Pp][Mm]')
SRPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.([Ss][Rr][Cc])\.[Rr][Pp][Mm]')
