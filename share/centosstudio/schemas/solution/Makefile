.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/schemas/solution
	install -pm 644 config-rpm.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/config.rng
	install -pm 644 iso.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/iso.rng
	install -pm 644 kickstart.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/kickstart.rng
	install -pm 644 lib.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/lib.rng
	install -pm 644 main.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/main.rng
	install -pm 644 packages.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/packages.rng
	install -pm 644 publish.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/publish.rng
	install -pm 644 repos.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/repos.rng
	install -pm 644 rpmbuild.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/rpmbuild.rng
	install -pm 644 test-install.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/test-install.rng
	install -pm 644 test-update.rng $(DESTDIR)/usr/share/centosstudio/schemas/solution/test-update.rng

clean:
