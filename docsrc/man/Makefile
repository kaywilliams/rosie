MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install repostudio.1.gz repostudio.conf.5.gz html

all: repostudio.1.gz repostudio.conf.5.gz

repostudio.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) repostudio.xml
	$(GZIP) repostudio.1

repostudio.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) repostudio.conf.xml
	$(GZIP) repostudio.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output repostudio.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl repostudio.xml
	$(XSLTPROC) --output repostudio.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl repostudio.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 repostudio.1.gz $(DESTDIR)/usr/share/man/man1/repostudio.1.gz
	install -m 644 repostudio.conf.5.gz $(DESTDIR)/usr/share/man/man5/repostudio.conf.5.gz

clean:
	rm -f repostudio.1.gz
	rm -f repostudio.conf.5.gz
	rm -f repostudio.1.html
	rm -f repostudio.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


