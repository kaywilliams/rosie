DOCGEN=../tools/docgen
all: spin.conf.5.gz distro.conf.5.gz

spin.conf.5.gz:
	$(DOCGEN) --xml-dir ./ --glob 'spin.rng' --output ./spin.conf.5.gz

distro.conf.5.gz:
	$(DOCGEN) --xml-dir ./ --glob '*rng' --nglob 'spin.rng' --output ./distro.conf.5.gz

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	install -m 644 spin.conf.5.gz $(DESTDIR)/usr/share/man/man5/spin.conf.5.gz
	install -m 644 distro.conf.5.gz $(DESTDIR)/usr/share/man/man5/distro.conf.5.gz
