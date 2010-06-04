srelease:
	dpkg-buildpackage -S -I.git -I.project -I.gitignore -I.pydevproject -Iold
	fakeroot ./debian/rules clean
	
brelease:
	dpkg-buildpackage -b -I.git -I.project -I.gitignore -I.pydevproject -Iold
	fakeroot ./debian/rules clean
