MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install deploy.1.gz deploy.conf.5.gz html

all: deploy.1.gz deploy.conf.5.gz

deploy.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) deploy.xml
	$(GZIP) deploy.1

deploy.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) deploy.conf.xml
	$(GZIP) deploy.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output deploy.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl deploy.xml
	$(XSLTPROC) --output deploy.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl deploy.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 deploy.1.gz $(DESTDIR)/usr/share/man/man1/deploy.1.gz
	install -m 644 deploy.conf.5.gz $(DESTDIR)/usr/share/man/man5/deploy.conf.5.gz

clean:
	rm -f deploy.1.gz
	rm -f deploy.conf.5.gz
	rm -f deploy.1.html
	rm -f deploy.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


