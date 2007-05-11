from event import EVENT_TYPE_META

from lib import InstallerInterface

from bootiso    import EVENTS as bootiso_EVENTS, isolinux_hook, bootiso_hook
from pxeboot    import EVENTS as pxeboot_EVENTS, pxeboot_hook
from rpmextract import EVENTS as rpmextract_EVENTS, preinstaller_logos_hook, installer_logos_hook, preinstaller_release_files_hook, installer_release_files_hook
from stage2     import EVENTS as stage2_EVENTS, stage2_hook
from xen        import EVENTS as xen_EVENTS, xen_hook
from updates    import EVENTS as updates_EVENTS, updates_hook

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
    'provides': ['INSTALLER'],
    'requires': ['.discinfo', 'software'],
  },
]
EVENTS.extend(stage2_EVENTS)
EVENTS.extend(pxeboot_EVENTS)
EVENTS.extend(bootiso_EVENTS)
EVENTS.extend(rpmextract_EVENTS)
EVENTS.extend(xen_EVENTS)
EVENTS.extend(updates_EVENTS)
