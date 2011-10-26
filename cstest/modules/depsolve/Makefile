all : depsolve-test-repos1.repo depsolve-test-repos2.repo depsolve-test-repos3.repo depsolve-test-repos4.repo depsolve-test-repos5.repo

depsolve-test-repos1.repo: depsolve-test-repos1.xml
	buildrepos --config-file depsolve-test-repos1.xml \
	--repo-file /tmp/cstest/depsolve-test-repos1.repo

depsolve-test-repos2.repo: depsolve-test-repos2.xml
	buildrepos --config-file depsolve-test-repos2.xml \
	--repo-file /tmp/cstest/depsolve-test-repos2.repo

depsolve-test-repos3.repo: depsolve-test-repos3.xml
	buildrepos --config-file depsolve-test-repos3.xml \
	--repo-file /tmp/cstest/depsolve-test-repos3.repo

depsolve-test-repos4.repo: depsolve-test-repos4.xml
	buildrepos --config-file depsolve-test-repos4.xml \
	--repo-file /tmp/cstest/depsolve-test-repos4.repo

depsolve-test-repos5.repo: depsolve-test-repos5.xml
	buildrepos --config-file depsolve-test-repos5.xml \
	--repo-file /tmp/cstest/depsolve-test-repos5.repo

clean :
	rm -rf repo1; rm -rf repo2; rm -rf repo3; \
	rm -rf repo4; rm -rf repo5; rm -f depsolve-test-*.repo
