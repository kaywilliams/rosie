all : depsolve-test-repos1.repo depsolve-test-repos2.repo depsolve-test-repos3.repo depsolve-test-repos4.repo

depsolve-test-repos1.repo: depsolve-test-repos1.xml
	buildrepos --config-file depsolve-test-repos1.xml \
	--repo-file depsolve-test-repos1.repo

depsolve-test-repos2.repo: depsolve-test-repos2.xml
	buildrepos --config-file depsolve-test-repos2.xml \
	--repo-file depsolve-test-repos2.repo

depsolve-test-repos3.repo: depsolve-test-repos3.xml
	buildrepos --config-file depsolve-test-repos3.xml \
	--repo-file depsolve-test-repos3.repo

depsolve-test-repos4.repo: depsolve-test-repos4.xml
	buildrepos --config-file depsolve-test-repos4.xml \
	--repo-file depsolve-test-repos4.repo

clean :
	rm -rf repo1; rm -rf repo2; rm -rf repo3; \
	rm -rf repo4; rm -f depsolve-test-*.repo
