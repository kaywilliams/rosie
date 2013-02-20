RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/deploy/schemas/repo
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/deploy/schemas/repo

clean:
