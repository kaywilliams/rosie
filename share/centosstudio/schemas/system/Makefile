.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/schemas/system
	install -pm 644 config-rpm.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/config.rng
	install -pm 644 iso.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/iso.rng
	install -pm 644 kickstart.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/kickstart.rng
	install -pm 644 lib.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/lib.rng
	install -pm 644 main.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/main.rng
	install -pm 644 packages.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/packages.rng
	install -pm 644 publish.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/publish.rng
	install -pm 644 repos.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/repos.rng
	install -pm 644 rpmbuild.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/rpmbuild.rng
	install -pm 644 test-install.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/test-install.rng
	install -pm 644 test-update.rng $(DESTDIR)/usr/share/centosstudio/schemas/system/test-update.rng

clean:
