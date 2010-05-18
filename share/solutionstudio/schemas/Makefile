SUBDIRS = distribution

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/solutionstudio/schemas
	install -pm 644 solutionstudio.rng $(DESTDIR)/usr/share/solutionstudio/schemas/solutionstudio.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
