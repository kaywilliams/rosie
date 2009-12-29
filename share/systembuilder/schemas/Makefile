SUBDIRS = distribution

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systembuilder/schemas
	install -pm 644 systembuilder.rng $(DESTDIR)/usr/share/systembuilder/schemas/systembuilder.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
