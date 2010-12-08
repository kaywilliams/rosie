SUBDIRS = system 

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/systemstudio/schemas
	install -pm 644 systemstudio.rng $(DESTDIR)/usr/share/systemstudio/schemas/systemstudio.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
