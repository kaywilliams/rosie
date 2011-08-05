SUBDIRS = distribution 

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/openprovision/schemas
	install -pm 644 openprovision.rng $(DESTDIR)/usr/share/openprovision/schemas/openprovision.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
