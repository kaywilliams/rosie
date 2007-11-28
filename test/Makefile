SUBDIRS = modules/download modules/pkglist

all:
	for d in $(SUBDIRS); do make -C $$d; done
clean:
	for d in $(SUBDIRS); do make -C $$d clean; done
