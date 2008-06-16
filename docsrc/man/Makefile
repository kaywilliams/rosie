MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

MANGEN   = ./tools/rst2man.py
XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

all: spin.conf.5.gz distro.conf.5.gz spin.1.gz

spin.1.gz:
	@$(XSLTPROC) $(MANXSL) spin.xml
	@$(GZIP) spin.1

spin.conf.5.gz:
	@$(XSLTPROC) $(MANXSL) spin.conf.xml
	@$(GZIP) spin.conf.5

distro.conf.5.gz:
	@$(MANGEN) distro/main.rst > distro.conf.5
	@$(GZIP) distro.conf.5

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 distro.conf.5.gz $(DESTDIR)/usr/share/man/man5/distro.conf.5.gz
	install -m 644 spin.1.gz $(DESTDIR)/usr/share/man/man1/spin.1.gz
	install -m 644 spin.conf.5.gz $(DESTDIR)/usr/share/man/man5/spin.conf.5.gz

clean:
	@rm -f distro.conf.5.gz
	@rm -f spin.1.gz
	@rm -f spin.conf.5.gz
