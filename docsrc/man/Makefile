MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install openprovision.1.gz openprovision.conf.5.gz html

all: openprovision.1.gz openprovision.conf.5.gz

openprovision.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) openprovision.xml
	$(GZIP) openprovision.1

openprovision.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) openprovision.conf.xml
	$(GZIP) openprovision.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output openprovision.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl openprovision.xml
	$(XSLTPROC) --output openprovision.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl openprovision.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 openprovision.1.gz $(DESTDIR)/usr/share/man/man1/openprovision.1.gz
	install -m 644 openprovision.conf.5.gz $(DESTDIR)/usr/share/man/man5/openprovision.conf.5.gz

clean:
	rm -f openprovision.1.gz
	rm -f openprovision.conf.5.gz
	rm -f openprovision.1.html
	rm -f openprovision.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


