RNGFILES = $(wildcard *.rng)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/schemas/solution
	cp -var $(RNGFILES) $(DESTDIR)/usr/share/centosstudio/schemas/solution

clean:
