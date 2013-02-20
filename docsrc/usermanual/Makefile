PUBLICAN = /usr/bin/publican
DRUSH = /usr/bin/drush
PUBDIR = /var/www/html/drupal/deployproject.org/files/docs/usermanual
THEMESDIR = /var/www/html/drupal/deployproject.org/themes/deployproject


.PHONY: all html pdf publish checkpkg clean

all: html pdf

html: 
	@make checkpkg BINARY=$(PUBLICAN)  INSTRUCTIONS="Install the publican package."
	../common.sh --clean-tmpdir html-single
	$(PUBLICAN) build --formats html-single --langs en-US --quiet

pdf: 
	@make checkpkg BINARY=$(PUBLICAN)  INSTRUCTIONS="Install the publican package."
	../common.sh --clean-tmpdir pdf
	$(PUBLICAN) build --formats pdf --langs en-US --quiet

publish:
	# publish user manual to drupal
	@make checkpkg BINARY=$(PUBLICAN)  INSTRUCTIONS="Install the publican package."
	
	# start clean
	rm -rf $(PUBDIR)/en-US 
	mkdir -p $(PUBDIR)/en-US

	# copy pdf folder to pubdir
	cp -a ./tmp/en-US/pdf $(PUBDIR)/en-US/

	# copy html-single files to pubdir (minus Common_Content)
	mkdir $(PUBDIR)/en-US/html-single
	for f in `ls ./tmp/en-US/html-single | grep -v Common_Content`; do \
	  cp -a ./tmp/en-US/html-single/$$f $(PUBDIR)/en-US/html-single; \
	done

	# modify src attributes in html file
	sed -i 's|src="\.|src="../../sites/deployproject.org/files/docs/usermanual/en-US/html-single|g' $(PUBDIR)/en-US/html-single/index.html

        # add metadata providing the desired path alias
	sed -i 's/<head>/<head><meta name="pathalias" content="docs\/usermanual"/g' $(PUBDIR)/en-US/html-single/index.html

        # set permissions
	chown -R apache:apache $(PUBDIR)/en-US/$d
	restorecon -R $(PUBDIR)/en-US/$d

	# import html-single into drupal
	# user manual feed node in Drupal is 5359
	# future - create a feed node dynanically and use it 
	$(DRUSH) php-eval "while (FEEDS_BATCH_COMPLETE != feeds_source('htmldocumentation', 5359)->import());"

	# copy Common_Content to themesdir
	# $(THEMESDIR)/deployproject.info makes reference to these files
	rm -rf $(THEMESDIR)/Common_Content
	cp -a ./tmp/en-US/html-single/Common_Content $(THEMESDIR)
	restorecon -R $(THEMESDIR)/Common_Content
	$(DRUSH) cache-clear css-js

	# copy templates to tmpldir
	../common.sh --copy-templates

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi

clean:
	rm -rf tmp
