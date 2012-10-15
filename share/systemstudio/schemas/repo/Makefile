RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systemstudio/schemas/repo
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/systemstudio/schemas/repo

clean:
