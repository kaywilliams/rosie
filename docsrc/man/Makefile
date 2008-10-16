MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install spin.1.gz spin.conf.5.gz man2html

all: spin.1.gz spin.conf.5.gz

spin.1.gz: checkpkgs
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	@$(GZIP) spin.1

spin.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	@$(XSLTPROC) $(MANXSL) spin.conf.xml
	@$(GZIP) spin.conf.5

man2html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output spin.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl spin.xml
	$(XSLTPROC) --output spin.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl spin.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 spin.1.gz $(DESTDIR)/usr/share/man/man1/spin.1.gz
	install -m 644 spin.conf.5.gz $(DESTDIR)/usr/share/man/man5/spin.conf.5.gz

clean:
	rm -f spin.1.gz
	rm -f spin.conf.5.gz
	rm -f spin.1.html
	rm -f spin.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


