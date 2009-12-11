.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm
	install -pm 644 GdmGreeterTheme.desktop $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/GdmGreeterTheme.desktop
	install -pm 644 Spin.gtkrc $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/Spin.gtkrc
	install -pm 644 SpinGDM.xml $(DESTDIR)/usr/share/systembuilder/logos-rpm/files/gdm/SpinGDM.xml

clean:
