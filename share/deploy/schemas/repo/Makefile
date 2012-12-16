RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/repo/schemas/repo
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/repo/schemas/repo

clean:
