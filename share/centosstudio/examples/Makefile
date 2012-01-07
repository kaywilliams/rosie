EXAMPLE_FILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/examples
	cp -var $(EXAMPLE_FILES) $(DESTDIR)/usr/share/centosstudio/examples

clean:
