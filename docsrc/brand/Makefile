PUBLICAN = /usr/bin/publican

.PHONY: all clean publish

all: publish 

publish:
	@make checkpkg BINARY=$(PUBLICAN)  INSTRUCTIONS="Install the publican package."
	$(PUBLICAN) build --formats xml --langs all --publish
	$(PUBLICAN) install_brand --path /usr/share/publican/Common_Content

checkpkg:
	@if [ ! -e $(BINARY) ]; then \
		echo "ERROR: $(BINARY) not found. $(INSTRUCTIONS)"; \
		exit 1; \
	fi

clean:
	rm -f tmp 
	rm -f publish
