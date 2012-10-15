MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkpkg clean install systemstudio.1.gz systemstudio.conf.5.gz html

all: systemstudio.1.gz systemstudio.conf.5.gz

systemstudio.1.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) systemstudio.xml
	$(GZIP) systemstudio.1

systemstudio.conf.5.gz:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(MANXSL) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XSLTPROC) $(MANXSL) systemstudio.conf.xml
	$(GZIP) systemstudio.conf.5

html:
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XSLTPROC) --output systemstudio.1.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl systemstudio.xml
	$(XSLTPROC) --output systemstudio.conf.5.html /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl systemstudio.conf.xml

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 systemstudio.1.gz $(DESTDIR)/usr/share/man/man1/systemstudio.1.gz
	install -m 644 systemstudio.conf.5.gz $(DESTDIR)/usr/share/man/man5/systemstudio.conf.5.gz

clean:
	rm -f systemstudio.1.gz
	rm -f systemstudio.conf.5.gz
	rm -f systemstudio.1.html
	rm -f systemstudio.conf.5.html

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


