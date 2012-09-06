RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/repostudio/schemas/repo
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/repostudio/schemas/repo

clean:
