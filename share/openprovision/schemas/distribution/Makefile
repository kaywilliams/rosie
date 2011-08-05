.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/openprovision/schemas/distribution
	install -pm 644 bootiso.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/bootiso.rng
	install -pm 644 chroot.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/chroot.rng
	install -pm 644 config.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/config.rng
	install -pm 644 deploy.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/deploy.rng
	install -pm 644 diskboot-image.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/diskboot-image.rng
	install -pm 644 iso.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/iso.rng
	install -pm 644 kickstart.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/kickstart.rng
	install -pm 644 lib.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/lib.rng
	install -pm 644 main.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/main.rng
	install -pm 644 packages.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/packages.rng
	install -pm 644 publish.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/publish.rng
	install -pm 644 repos.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/repos.rng
	install -pm 644 rpmbuild.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/rpmbuild.rng
	install -pm 644 test.rng $(DESTDIR)/usr/share/openprovision/schemas/distribution/test.rng

clean:
