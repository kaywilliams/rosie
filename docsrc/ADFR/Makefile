DBLATEX  = /usr/bin/dblatex
XMLLINT  = /usr/bin/xmllint
XSLTPROC = /usr/bin/xsltproc

.PHONY: all ADFR.html ADFR.pdf checkpkg clean install

all: ADFR.html

install:

ADFR.html:
	@make checkpkg BINARY=$(XMLLINT)  INSTRUCTIONS="Install the libxml2 package."
	@make checkpkg BINARY=$(XSLTPROC) INSTRUCTIONS="Install the libxslt package."
	$(XMLLINT) --output Index_tmp.xml --xinclude Index.xml
	sed -i 's|\\\$$|\$$|g' Index_tmp.xml
	$(XSLTPROC) --output ADFR.html \
	            --stringparam generate.toc "book toc,title" \
                    --stringparam toc.max.depth 2 \
                    --stringparam admon.graphics 1 \
                    --stringparam admon.graphics.extension .png \
                    --stringparam callout.graphics.extension .png \
                    --stringparam chapter.autolabel 1 \
                    --stringparam section.autolabel 1 \
                    --stringparam section.label.includes.component.label 1 \
                    --stringparam section.autolabel.max.depth 1 \
                    /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl Index_tmp.xml
	rm -f Index_tmp.xml

ADFR.pdf:
	@make checkpkg BINARY=$(DBLATEX) INSTRUCTIONS="Install the dblatex package."
	$(DBLATEX) -o ADFR.pdf -P toc.section.depth=1 -P doc.section.depth=1 -S ../dblatex/spindocs.specs --pdf Index.xml

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi

clean:
	rm -f ADFR.html
	rm -f ADFR.pdf
