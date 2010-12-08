MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install systembuilder.1.gz systembuilder.conf.5.gz html

all: systembuilder.1.gz systembuilder.conf.5.gz

systembuilder.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) systembuilder.xml
	$(GZIP) systembuilder.1

systembuilder.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) systembuilder.conf.xml
	$(GZIP) systembuilder.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output systembuilder.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl systembuilder.xml
	$(XSLTPROC) --output systembuilder.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl systembuilder.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 systembuilder.1.gz $(DESTDIR)/usr/share/man/man1/systembuilder.1.gz
	install -m 644 systembuilder.conf.5.gz $(DESTDIR)/usr/share/man/man5/systembuilder.conf.5.gz

clean:
	rm -f systembuilder.1.gz
	rm -f systembuilder.conf.5.gz
	rm -f systembuilder.1.html
	rm -f systembuilder.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


