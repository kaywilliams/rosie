from rendition import pps
from rendition import rxml

root = rxml.config.Element('logos-rpm')

for icon in pps.path('icons').findpaths():
    gdm = rxml.config.Element('file', parent=root,
                            attrs={'dest': '/usr/share/apps/gdm/themes/Spin/%s' % icon.basename,
                                   'xwindow-type': 'gnome'})
    rxml.config.Element('path', parent=gdm, text='icons/%s' % icon.basename)

for icon in pps.path('icons').findpaths():
    kde = rxml.config.Element('file', parent=root,
                            attrs={'dest': '/usr/share/apps/kdm/themes/Spin/%s' % icon.basename,
                                   'xwindow-type': 'kde'})
    rxml.config.Element('path', parent=kde, text='icons/%s' % icon.basename)

for icon in pps.path('icons').findpaths():
    kder = rxml.config.Element('file', parent=root,
                             attrs={'dest': '/usr/share/apps/kdm/themes/Spin/%s' % icon.basename,
                                    'xwindow-type': 'kde',
                                    'anaconda-version': '11.3.0.36-1'})
    rxml.config.Element('remove', parent=kder, text='True')

for icon in pps.path('icons').findpaths():
    kde4 = rxml.config.Element('file', parent=root,
                             attrs={'dest': '/usr/share/kde4/apps/kdm/themes/Spin/%s' % icon.basename,
                                    'xwindow-type': 'kde',
                                    'anaconda-version': '11.3.0.36-1'})
    rxml.config.Element('path', parent=kde4, text='icons/%s' % icon.basename)
print root
