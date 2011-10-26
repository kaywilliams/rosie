MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install centosstudio.1.gz centosstudio.conf.5.gz html

all: centosstudio.1.gz centosstudio.conf.5.gz

centosstudio.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) centosstudio.xml
	$(GZIP) centosstudio.1

centosstudio.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) centosstudio.conf.xml
	$(GZIP) centosstudio.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output centosstudio.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl centosstudio.xml
	$(XSLTPROC) --output centosstudio.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl centosstudio.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 centosstudio.1.gz $(DESTDIR)/usr/share/man/man1/centosstudio.1.gz
	install -m 644 centosstudio.conf.5.gz $(DESTDIR)/usr/share/man/man5/centosstudio.conf.5.gz

clean:
	rm -f centosstudio.1.gz
	rm -f centosstudio.conf.5.gz
	rm -f centosstudio.1.html
	rm -f centosstudio.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


