MANGEN = ./tools/rst2man.py
GZIP = gzip
all: spin.conf.5.gz distro.conf.5.gz

spin.conf.5.gz:
	@$(MANGEN) spin/spin.rst > spin.conf.5
	@$(GZIP) spin.conf.5

distro.conf.5.gz:
	@$(MANGEN) distro/main.rst > distro.conf.5
	@$(GZIP) distro.conf.5

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	install -m 644 spin.conf.5.gz $(DESTDIR)/usr/share/man/man5/spin.conf.5.gz
	install -m 644 distro.conf.5.gz $(DESTDIR)/usr/share/man/man5/distro.conf.5.gz

clean:
	@rm -f spin.conf.5.gz
	@rm -f distro.conf.5.gz
