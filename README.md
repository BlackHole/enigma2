## OpenBh buildserver requirements: ##

>Ubuntu 24.04 LTS (GNU/Linux 6.8.0-39-generic x86_64)

## minimum hardware requirement for image build (building feeds may require more):

> RAM:  16GB
> SWAP: 16GB (if building feeds then RAM+SWAP should be larger)>
> CPU:  Multi core\thread Model
> HDD:  for Single Build 250GB Free, for Multibuild 500GB or more

## OpenBh python3 is built using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/5.4](https://github.com/oe-alliance/oe-alliance-core/tree/5.4 "OE-Alliance")
>
> https://github.com/BlackHole/enigma2

----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-12 gcc-multilib g++-multilib gettext git git-core gzip help2man info iputils-ping java-common libc6-dev libegl1-mesa libglib2.0-dev libncurses5-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python-setuptools qemu quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev zstd fakeroot lz4 liblz4-tool

----------
2 - Set python3 as preferred provider for python

	sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1
	sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2
	sudo update-alternatives --config python
	select python3

----------
3 - Set your shell to /bin/bash.

    sudo ln -sf /bin/bash /bin/sh

----------
4 - modify max_user_watches

	echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

	sudo sysctl -n -w fs.inotify.max_user_watches=524288

----------
5. Disable apparmor profile
   Currently due to this Ubuntu/bitbake issue..https://bugs.launchpad.net/ubuntu/+source/apparmor/+bug/2056555
   This command must be entered after every restart of the build PC....

   sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0

----------
6 - Add user openbhbuilder

----------
7. Add your git user and email

     git config --global user.email "you@example.com"

    git config --global user.name "Your Name"

----------
8 - Switch to user openbhbuilder

----------
9 - Switch to home of openbhbuilder

	cd ~

----------
10 - Create folder openbh

	mkdir -p ~/openbh

----------
11 - Switch to folder openbh

	cd openbh

----------
12 - Clone oe-alliance git

    git clone https://github.com/oe-alliance/build-enviroment.git -b 5.4

----------
13 - Switch to folder build-enviroment

	cd build-enviroment

----------
14 - Update build-enviroment

	make update

----------
15 - Initialise the first machine so site.conf gets created

    MACHINE=vuultimo4k DISTRO=openbh DISTRO_TYPE=release make  init

----------
16 - Update site.conf

    - BB_NUMBER_THREADS, PARALLEL_MAKE set to number of threads supported by the CPU
    - add/modify DL_DIR = " location for build sources " to point to a location where you can save derived build sources,
    this will reduce build time in fetching these sources again.

----------
17 - Building image with feeds  e.g.:-

	MACHINE=vuultimo4k DISTRO=openbh DISTRO_TYPE=release make image

----------
18 - Building an image without feeds (Build time 1-2h)

	MACHINE=vuultimo4k DISTRO=openbh DISTRO_TYPE=release make enigma2-image

----------
19 - Building feeds only

	MACHINE=vuultimo4k DISTRO=openbh DISTRO_TYPE=release make feeds

