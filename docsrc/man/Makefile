MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

.PHONY: all checkdocbook checlibxslt checkpkg checkpkgs clean install spin.1.gz spin.conf.5.gz

all: spin.1.gz spin.conf.5.gz

spin.1.gz: checkpkgs
	@$(XSLTPROC) $(MANXSL) spin.xml
	@$(GZIP) spin.1

spin.conf.5.gz: checkpkgs
	@$(XSLTPROC) $(MANXSL) spin.conf.xml
	@$(GZIP) spin.conf.5

install:
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/man/man1
	install -m 644 spin.1.gz $(DESTDIR)/usr/share/man/man1/spin.1.gz
	install -m 644 spin.conf.5.gz $(DESTDIR)/usr/share/man/man5/spin.conf.5.gz

clean:
	@rm -f spin.1.gz
	@rm -f spin.conf.5.gz

checkpkgs:
	@make --no-print-directory checkdocbook
	@make --no-print-directory checklibxslt

checklibxslt: FILE = $(XSLTPROC)
checklibxslt: INSTRUCTIONS = "Install the libxslt package."
checklibxslt: checkpkg

checkdocbook: FILE = $(MANXSL)
checkdocbook: INSTRUCTIONS = "Install the docbook-style-xsl package."
checkdocbook: checkpkg

checkpkg:
	@if [ ! -e $(FILE) ]; then \
		echo "ERROR: $(FILE) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi


