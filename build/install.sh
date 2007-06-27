python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

CONFIG_DIR=$RPM_BUILD_ROOT/etc/dimsbuild

mkdir -p $CONFIG_DIR
install -m 644 conf/dimsbuild.conf $CONFIG_DIR/dimsbuild.conf

EXAMPLES="example-fedora-base-6 example-fedora-base-7 example-centos-base-5 example-redhat-base-5"
for example in $EXAMPLES; do
    mkdir -p $CONFIG_DIR/$example
    install -m 644 conf/$example/distro.conf $CONFIG_DIR/$example/distro.conf
done

DOC_FILES="ChangeLog"
mkdir -p $RPM_BUILD_ROOT/usr/share/doc/dimsbuild
for file in $DOC_FILES; do
    install -m 644 share/doc/$file $RPM_BUILD_ROOT/usr/share/doc/dimsbuild/$file
done
echo /usr/share/doc/dimsbuild >> INSTALLED_FILES
