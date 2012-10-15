EXAMPLE_FILES = $(wildcard *)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systemstudio/templates
	cp -var $(EXAMPLE_FILES) $(DESTDIR)/usr/share/systemstudio/templates

clean:
