.PHONY: all clean install

all:

install:
	find ./ ! \( -name execlib.py -o \
                     -name i18n.py -o \
                     -name permute.py -o \
                     -name rpmbind.py -o \
                     -name seqlib.py -o \
                     -name textfmt.py -o \
                     -wholename "*pps/test*" \)| \
        cpio -pdvm $(DESTDIR)/$(PYTHONLIBDIR)/systembuilder/util

clean:
	find ./ -name "*.pyo" -o -name "*.pyc" -type f -print0 | \
        xargs -0 /bin/rm -f 
