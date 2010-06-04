MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install solutionstudio.1.gz solutionstudio.conf.5.gz html

all: solutionstudio.1.gz solutionstudio.conf.5.gz

solutionstudio.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) solutionstudio.xml
	$(GZIP) solutionstudio.1

solutionstudio.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) solutionstudio.conf.xml
	$(GZIP) solutionstudio.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output solutionstudio.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl solutionstudio.xml
	$(XSLTPROC) --output solutionstudio.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl solutionstudio.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 solutionstudio.1.gz $(DESTDIR)/usr/share/man/man1/solutionstudio.1.gz
	install -m 644 solutionstudio.conf.5.gz $(DESTDIR)/usr/share/man/man5/solutionstudio.conf.5.gz

clean:
	rm -f solutionstudio.1.gz
	rm -f solutionstudio.conf.5.gz
	rm -f solutionstudio.1.html
	rm -f solutionstudio.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


