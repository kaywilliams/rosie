SUBDIRS = system 

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/centosstudio/schemas
	install -pm 644 centosstudio.rng $(DESTDIR)/usr/share/centosstudio/schemas/centosstudio.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
