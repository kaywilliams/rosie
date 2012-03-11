RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/schemas/repo
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/centosstudio/schemas/repo

clean:
