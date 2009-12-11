.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm
	install -pm 644 GdmGreeterTheme.desktop $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/GdmGreeterTheme.desktop
	install -pm 644 SystemBuilder.gtkrc $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/SystemBuilder.gtkrc
	install -pm 644 SystemBuilderGDM.xml $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/SystemBuilderGDM.xml

clean:
