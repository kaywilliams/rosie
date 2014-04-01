MANXSL = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl

XSLTPROC = /usr/bin/xsltproc
GZIP = /bin/gzip

DRUSH = /usr/bin/drush
PUBDIR = /var/www/html/drupal/deployproject.org/files/docs/man

.PHONY: all checkpkg clean install deploy.1.gz deploy.conf.5.gz html publish 

all: deploy.1.gz deploy.conf.5.gz html

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

publish:
	# start clean
	rm -rf $(PUBDIR)/en-US 
	mkdir -p $(PUBDIR)/en-US

	# copy html files to pubdir
	cp -a *.html $(PUBDIR)/en-US; \

        # add metadata providing the desired path alias
	sed -i 's/<head>/<head><meta name="pathalias" content="docs\/deploy"\/>/g' $(PUBDIR)/en-US/deploy.1.html
	sed -i 's/<head>/<head><meta name="pathalias" content="docs\/deploy.conf"\/>/g' $(PUBDIR)/en-US/deploy.conf.5.html

        # set permissions
	chown -R apache:apache $(PUBDIR)/en-US/$d
	restorecon -R $(PUBDIR)/en-US/$d

	# import man pages into drupal
	# deploy feed node in Drupal is 5378
	# deploy.conf feed node in Drupal is 5379
	# future - create a feed node dynanically and use it 
	$(DRUSH) php-eval "while (FEEDS_BATCH_COMPLETE != feeds_source('htmldocumentation', 5378)->import());"
	$(DRUSH) php-eval "while (FEEDS_BATCH_COMPLETE != feeds_source('htmldocumentation', 5379)->import());"
	
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


