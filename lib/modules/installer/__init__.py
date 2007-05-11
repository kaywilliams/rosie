from event import EVENT_TYPE_META

from lib import InstallerInterface

from bootiso    import EVENTS as bootiso_EVENTS, preisolinux_hook, isolinux_hook, prebootiso_hook, bootiso_hook
from pxeboot    import EVENTS as pxeboot_EVENTS, pxeboot_hook
from rpmextract import EVENTS as rpmextract_EVENTS, preinstaller_logos_hook, installer_logos_hook, preinstaller_release_files_hook, installer_release_files_hook
from stage2     import EVENTS as stage2_EVENTS, stage2_hook
from xen        import EVENTS as xen_EVENTS, prexen_hook, xen_hook
from updates    import EVENTS as updates_EVENTS, preupdates_hook, updates_hook
from product    import EVENTS as product_EVENTS, preproduct_hook, product_hook

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
EVENTS.extend(product_EVENTS)
