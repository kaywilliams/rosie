DBLATEX  = /usr/bin/dblatex
XMLLINT  = /usr/bin/xmllint
XSLTPROC = /usr/bin/xsltproc

HTML_STYLESHEET = /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl

.PHONY: all RDFR.html RDFR.pdf checkpkg clean install

all: RDFR.html

install:

RDFR.html:
	@make checkpkg BINARY=$(XMLLINT)  INSTRUCTIONS="Install the libxml2 package."
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	@make checkpkg BINARY=$(HTML_STYLESHEET) INSTRUCTIONS="Install the docbook-style-xsl package."
	$(XMLLINT) --output Index_tmp.xml --xinclude Index.xml
	sed -i 's|\\\$$|\$$|g' Index_tmp.xml
	$(XSLTPROC) --output RDFR.html \
	            --stringparam generate.toc "book toc,title" \
                    --stringparam toc.max.depth 2 \
                    --stringparam admon.graphics 1 \
                    --stringparam admon.graphics.extension .png \
                    --stringparam callout.graphics.extension .png \
                    --stringparam chapter.autolabel 1 \
                    --stringparam section.autolabel 1 \
                    --stringparam section.label.includes.component.label 1 \
                    --stringparam section.autolabel.max.depth 1 \
                    $(HTML_STYLESHEET) Index_tmp.xml
	rm -f Index_tmp.xml

RDFR.pdf:
	@make checkpkg BINARY=$(DBLATEX) INSTRUCTIONS="Install the dblatex package."
	$(DBLATEX) -o RDFR.pdf -P toc.section.depth=1 -P doc.section.depth=1 -S ../dblatex/systemstudiodocs.specs --pdf Index.xml

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi

clean:
	rm -f RDFR.html
	rm -f RDFR.pdf
