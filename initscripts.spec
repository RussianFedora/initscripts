Summary: The inittab file and the /etc/init.d scripts.
Name: initscripts
Version: 5.85
Copyright: GPL
Group: System Environment/Base
Release: 1.71.2sx
Source: initscripts-%{version}.tar.gz
Patch0: initscripts-s390x.patch
Patch1: initscripts-5.85-backport5841.patch
Patch2: initscripts-s390x-2.patch
BuildRoot: /%{_tmppath}/%{name}-%{version}-%{release}-root
Requires: mingetty, /bin/awk, /bin/sed, mktemp, e2fsprogs >= 1.15
Requires: procps >= 2.0.7-7, sysklogd >= 1.3.31
Requires: setup >= 2.0.3, /sbin/fuser, which
Requires: modutils >= 2.3.11-5
Requires: util-linux >= 2.10s-11, mount >= 2.10r-5
Requires: bash >= 2.0
Conflicts: kernel <= 2.2, timeconfig < 3.0, pppd < 2.3.9, wvdial < 1.40-3
Conflicts: ypbind < 1.6-12
Obsoletes: rhsound sapinit
Prereq: /sbin/chkconfig, /usr/sbin/groupadd, gawk, fileutils
BuildPrereq: glib-devel

%description
The initscripts package contains the basic system scripts used to boot
your Red Hat system, change runlevels, and shut the system down
cleanly.  Initscripts also contains the scripts that activate and
deactivate most network interfaces.


%prep
%setup -q
%patch0 -p1
%patch1 -p1
%patch2 -p1
chmod 755 sysconfig/network-scripts/ifup-escon

%build
make

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc
make ROOT=$RPM_BUILD_ROOT SUPERUSER=`id -un` SUPERGROUP=`id -gn` mandir=%{_mandir} install 
mkdir -p $RPM_BUILD_ROOT/var/run/netreport
#chown root.root $RPM_BUILD_ROOT/var/run/netreport
chmod u=rwx,g=rwx,o=rx $RPM_BUILD_ROOT/var/run/netreport

for i in 0 1 2 3 4 5 6 ; do
  file=$RPM_BUILD_ROOT/etc/rc.d/rc$i.d
  mkdir $file
# chown root.root $file
  chmod u=rwx,g=rx,o=rx $file
done

# Can't store symlinks in a CVS archive
ln -s ../init.d/killall $RPM_BUILD_ROOT/etc/rc.d/rc0.d/S00killall
ln -s ../init.d/killall $RPM_BUILD_ROOT/etc/rc.d/rc6.d/S00killall

ln -s ../init.d/halt $RPM_BUILD_ROOT/etc/rc.d/rc0.d/S01halt
ln -s ../init.d/halt $RPM_BUILD_ROOT/etc/rc.d/rc6.d/S01reboot

ln -s ../init.d/single $RPM_BUILD_ROOT/etc/rc.d/rc1.d/S00single

ln -s ../rc.local $RPM_BUILD_ROOT/etc/rc.d/rc2.d/S99local
ln -s ../rc.local $RPM_BUILD_ROOT/etc/rc.d/rc3.d/S99local
ln -s ../rc.local $RPM_BUILD_ROOT/etc/rc.d/rc5.d/S99local

# These are LSB compatibility symlinks.  At some point in the future
# the actual files will be here instead of symlinks
for i in 0 1 2 3 4 5 6 ; do
  ln -s rc.d/rc$i.d $RPM_BUILD_ROOT/etc/rc$i.d
done
for i in rc rc.sysinit rc.local ; do
  ln -s rc.d/$i $RPM_BUILD_ROOT/etc/$i
done

mkdir -p $RPM_BUILD_ROOT/var/{log,run}
touch $RPM_BUILD_ROOT/var/run/utmp
touch $RPM_BUILD_ROOT/var/log/wtmp

# Put this stuff in /usr/share/locale too
mkdir -p $RPM_BUILD_ROOT/usr/share/locale
cp -a $RPM_BUILD_ROOT/etc/locale/* $RPM_BUILD_ROOT/usr/share/locale/

pushd %{buildroot}/%{_datadir}/locale
for foo in * ; do
 echo  "%lang($foo) %{_datadir}/locale/$foo/*/*" >> \
      $RPM_BUILD_DIR/%{name}-%{version}/trans.list
done
popd

pushd  %{buildroot}/etc/locale
for foo in * ; do
  echo "%lang($foo) /etc/locale/$foo/*/*" >> \
      $RPM_BUILD_DIR/%{name}-%{version}/trans.list
done
popd

%pre
/usr/sbin/groupadd -g 22 -r -f utmp

%post
touch /var/log/wtmp
touch /var/run/utmp
chown root.utmp /var/log/wtmp /var/run/utmp
chmod 664 /var/log/wtmp /var/run/utmp

chkconfig --add random 
chkconfig --add netfs 
chkconfig --add network 
chkconfig --add rawdevices

# handle serial installs semi gracefully
if [ $1 = 0 ]; then
  if [ "$TERM" = "vt100" ]; then
      tmpfile=/etc/sysconfig/tmp.$$
      sed -e '/BOOTUP=color/BOOTUP=serial/' /etc/sysconfig/init > $tmpfile
      mv -f $tmpfile /etc/sysconfig/init
  fi
fi

# dup of timeconfig %post - here to avoid a dependency
if [ -L /etc/localtime ]; then
    _FNAME=`ls -ld /etc/localtime | awk '{ print $11}' | sed 's/lib/share/'`
    rm /etc/localtime
    cp -f $_FNAME /etc/localtime
    if ! grep -q "^ZONE=" /etc/sysconfig/clock ; then
      echo "ZONE=\"$_FNAME"\" | sed -e "s|[^\"]*/usr/share/zoneinfo/||" >> /etc/sysconfig/clock
    fi
fi

%preun
if [ $1 = 0 ]; then
  chkconfig --del random
  chkconfig --del netfs
  chkconfig --del network
  chkconfig --del rawdevices
fi

%triggerpostun -- initscripts <= 5.04
/sbin/chkconfig --add random
/sbin/chkconfig --add netfs
/sbin/chkconfig --add network

%triggerpostun -- initscripts <= 4.72

. /etc/sysconfig/init
. /etc/sysconfig/network

# These are the non-default settings. By putting them at the end
# of the /etc/sysctl.conf file, it will override the default
# settings earlier in the file.

if [ -n "$FORWARD_IPV4" -a "$FORWARD_IPV4" != "no" -a "$FORWARD_IPV4" != "false" ]; then
	echo "# added by initscripts install on `date`" >> /etc/sysctl.conf
	echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
fi

newnet=`mktemp /etc/sysconfig/network.XXXXXX`
if [ -n "$newnet" ]; then
  sed "s|FORWARD_IPV4.*|# FORWARD_IPV4 removed; see /etc/sysctl.conf|g" \
   /etc/sysconfig/network > $newnet
  sed "s|DEFRAG_IPV4.*|# DEFRAG_IPV4 removed; obsolete in 2.4. kernel|g" \
   $newnet > /etc/sysconfig/network
  rm -f $newnet
fi

if [ -n "$MAGIC_SYSRQ" -a "$MAGIC_SYSRQ" != "no" ]; then
	echo "# added by initscripts install on `date`" >> /etc/sysctl.conf
	echo "kernel.sysrq = 1" >> /etc/sysctl.conf
fi
if uname -m | grep -q sparc ; then
   if [ -n "$STOP_A" -a "$STOP_A" != "no" ]; then
	echo "# added by initscripts install on `date`" >> /etc/sysctl.conf
	echo "kernel.stop-a = 1" >> /etc/sysctl.conf
   fi
fi

newinit=`mktemp /etc/sysconfig/init.XXXXXX`
if [ -n "$newinit" ]; then
  sed "s|MAGIC_SYSRQ.*|# MAGIC_SYSRQ removed; see /etc/sysctl.conf|g" \
   /etc/sysconfig/init > $newinit
  sed "s|STOP_A.*|# STOP_A removed; see /etc/sysctl.conf|g" \
   $newinit > /etc/sysconfig/init
  rm -f $newinit
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files -f trans.list
%defattr(-,root,root)
%dir /etc/sysconfig/network-scripts
%config(noreplace) %verify(not md5 mtime size) /etc/adjtime
%config(noreplace) /etc/sysconfig/init
/etc/sysconfig/network-scripts/ifdown
%config /sbin/ifdown
%config /etc/sysconfig/network-scripts/ifdown-post
/etc/sysconfig/network-scripts/ifup
%config /sbin/ifup
%dir /etc/sysconfig/console
%config(noreplace) /etc/sysconfig/rawdevices
%config /etc/sysconfig/network-scripts/network-functions
%config /etc/sysconfig/network-scripts/network-functions-ipv6
%config /etc/sysconfig/network-scripts/ifup-post
%config /etc/sysconfig/network-scripts/ifcfg-lo
%config /etc/sysconfig/network-scripts/ifdown-ppp
%config /etc/sysconfig/network-scripts/ifdown-sl
%config /etc/sysconfig/network-scripts/ifup-ppp
%config /etc/sysconfig/network-scripts/ifup-sl
%config /etc/sysconfig/network-scripts/ifup-routes
%config /etc/sysconfig/network-scripts/ifup-plip
%config /etc/sysconfig/network-scripts/ifup-plusb
%config /etc/sysconfig/network-scripts/ifup-ipv6
%config /etc/sysconfig/network-scripts/ifdown-ipv6
%config /etc/sysconfig/network-scripts/ifup-sit
%config /etc/sysconfig/network-scripts/ifdown-sit
%config /etc/sysconfig/network-scripts/ifup-aliases
%config /etc/sysconfig/network-scripts/ifup-ipx
%ifarch s390 s390x
%config /etc/sysconfig/network-scripts/ifup-ctc
%config /etc/sysconfig/network-scripts/ifup-escon
%config /etc/sysconfig/network-scripts/ifup-iucv
%endif
%config /etc/X11/prefdm
%config /etc/inittab
%dir /etc/rc.d
%dir /etc/rc.d/rc[0-9].d
%config(missingok) /etc/rc.d/rc[0-9].d/*
/etc/rc[0-9].d
/etc/rc
%dir /etc/rc.d/init.d
/etc/rc.local
/etc/rc.sysinit
%config /etc/rc.d/init.d/*
%config /etc/rc.d/rc
%config(noreplace) /etc/rc.d/rc.local
%config /etc/rc.d/rc.sysinit
%config(noreplace) /etc/sysctl.conf
%config /etc/profile.d/lang.sh
%config /etc/profile.d/lang.csh
/usr/sbin/sys-unconfig
/sbin/mkkerneldoth
/sbin/setsysfont
/bin/doexec
/bin/ipcalc
/bin/usleep
%attr(4755,root,root) /usr/sbin/usernetctl
/sbin/consoletype
/sbin/getkey
%attr(2755,root,root) /sbin/netreport
/sbin/initlog
/sbin/minilogd
/sbin/service
/sbin/ppp-watch
%{_mandir}/man*/*
%dir %attr(775,root,root) /var/run/netreport
%config /etc/ppp/ip-up
%config /etc/ppp/ip-down
%config /etc/initlog.conf
%doc sysconfig.txt sysvinitfiles ChangeLog static-routes-ipv6 ipv6-tunnel.howto
%ghost %attr(0664,root,utmp) /var/log/wtmp
%ghost %attr(0664,root,utmp) /var/run/utmp

%changelog
* Fri Feb 15 2002 Phil Knirsch <pknirsch@redhat.com>
- Added fixes for oco handling and ifup-ctc
- Added ifup-escon.

* Wed Jan 30 2002 David Sainty <dsainty@redhat.com> 5.85-1.71.1sx
- add in valid patches from 5.84.1-1 7.1 backport

* Wed Apr 25 2001 Florian La Roche <Florian.LaRoche@redhat.de>
- add further s390 changes:
	- ifup-iucv
	- mkkerneldoth.s390

* Tue Apr 24 2001 Than Ngo <than@redhat.com>
- add shutdown UPS into halt (bug #34312)

* Sat Apr  7 2001 Preston Brown <pbrown@redhat.com>
- broke out kernel.h updater from rc.sysinit into /sbin/mkkerneldoth

* Fri Apr  6 2001 Bill Nottingham <notting@redhat.com>
- be a little more careful in do_netreport (#34933)

* Tue Apr  3 2001 Bill Nottingham <notting@redhat.com>
- set umask explicitly to 022 in /etc/init.d/functions

* Mon Apr  2 2001 Bill Nottingham <notting@redhat.com>
- fix segfault in usernetctl (#34353)

* Mon Mar 26 2001 Bill Nottingham <notting@redhat.com>
- don't print errors in /etc/init.d/network if kernel.hotplug doesn't exist

* Thu Mar 22 2001 Erik Troan <ewt@redhat.com>
- take advantage of new swapon behaviors

* Wed Mar 14 2001 Bill Nottingham <notting@redhat.com>
- add cipe interfaces last (#31597)

* Tue Mar 13 2001 Bill Nottingham <notting@redhat.com>
- fix typo in ifup (#31627)
- update translation source

* Tue Mar 13 2001 Nalin Dahyabhai <nalin@redhat.com>
- fix typo in rc.sysinit
- fix ifup-routes not setting DEVICE properly

* Mon Mar 12 2001 Preston Brown <pbrown@redhat.com>
- Work properly with new quota utilities

* Mon Mar  5 2001 Bill Nottingham <notting@redhat.com>
- IPv6 fixes (#30506)
- make static-routes handling more sane and consistent (#29500, #29549)
- handle multiple USB controllers *correctly*

* Wed Feb 28 2001 Nalin Dahyabhai <nalin@redhat.com>
- usernetctl, ppp-watch: cleanups
- netreport: use O_NOFOLLOW
- ifup-ppp: let ppp-watch watch over demand-dialed connections (#28927)

* Tue Feb 27 2001 Bill Nottingham <notting@redhat.com>
- don't run isapnp on isapnp-enabled 2.4 kernels (part of #29450)
- disable hotplug during network initscript
- don't munge wireless keys in ifup; that will be done with the
  PCMCIA wireless stuff
- run sndconfig --mungepnp for non-native-isapnp soundcards
- don't explicitly kill things in init.d/single, init will do it
- don't explicitly load usb-storage; mount the usbdevfs before initializing
  host controller modules

* Wed Feb 21 2001 Bill Nottingham <notting@redhat.com>
- initialize multiple USB controllers if necessary

* Wed Feb 21 2001 Nalin Dahyabhai <nalin@redhat.com>
- close extra file descriptors before exec()ing commands in initlog

* Mon Feb 19 2001 Bill Nottingham <notting@redhat.com>
- fix some substitions in init.d/functions (fixes various killproc issues)
- make sure ipv6 module alias is available if configured
- fix initlog segfaults in popt when called with bogus stuff (#28140)

* Thu Feb 15 2001 Nalin Dahyabhai <nalin@redhat.com>
- make pidofproc() and killproc() try to use the PID associated with the full
  pathname first before killing the daemon by its basename (for daemons that
  share the same basename, i.e. "master" in postfix and cyrus-imapd) (#19016)
- fix status() as well

* Wed Feb 14 2001 Bill Nottingham <notting@redhat.com>
- fix init.d/single to work around possible kernel problem

* Tue Feb 13 2001 Bill Nottingham <notting@redhat.com>
- fix unmounting of loopback stuff (#26439, #14672)

* Mon Feb 12 2001 Bill Nottingham <notting@redhat.com>
- fix ifup-post so that it will work right when not called from ifup

* Sat Feb 10 2001 Florian La Roche <Florian.LaRoche@redhat.de>
- add all save changes for s390 s390x that won't break anything
  patches are from Oliver Paukstadt @ millenux.com

* Fri Feb  9 2001 Bill Nottingham <notting@redhat.com>
- muck with the font in lang.csh/lang.sh, but don't spit out errors (#26903)

* Wed Feb  7 2001 Bill Nottingham <notting@redhat.com>
- ipv6 sync ups (#26502, #25775)
- fix hangs at shutdown (#25744)
- fix ifup-ppp (#26323)

* Tue Feb  6 2001 Bill Nottingham <notting@redhat.com>
- modify firewall on ifup to allow any new DNS servers through (#25951)
- don't muck with the font in lang.csh/lang.sh (#26349)
- don't display Japanese if we aren't on a pty (#25041)
- load ide-scsi if passed on /proc/cmdline

* Mon Feb  5 2001 Trond Eivind Glomsr�d <teg@redhat.com>
- i18n updates

* Fri Feb  2 2001 Bill Nottingham <notting@redhat.com>
- actually *ship* the ipv6 (and plusb) files

* Thu Feb  1 2001 Trond Eivind Glomsr�d <teg@redhat.com>
- i18n updates

* Tue Jan 30 2001 Bill Nottingham <notting@redhat.com>
- various init.d/functions cleanups (#10761, from <mjt@tls.msk.ru>)
- in daemon(), only look at pidfile to determine if process is running
  (#17244, others)
- ifup-ppp enhancements (#17388, from <ayn2@cornell.edu>)
- ipv6 support (#23576, originally by Peter Bieringer <pb@bieringer.de>)
- lots of other minor fixes (see ChangeLog)

* Mon Jan 29 2001 Bill Nottingham <notting@redhat.com>
- add plusb support (#18892, patch from <eric.ayers@compgen.com>)
- don't ignore RETRYTIMEOUT when we never connect (#14071, patch from
  <ak@cave.hop.stu.neva.ru>)

* Wed Jan 24 2001 Bill Nottingham <notting@redhat.com>
- quiet LVM setup (#24841)
- fix inability to shutdown cleanly (#24889)

* Tue Jan 23 2001 Bill Nottingham <notting@redhat.com>
- new i18n mechanism

* Tue Jan 23 2001 Matt Wilson <msw@redhat.com>
- fixed typo in init.d/network - missing | in pipeline

* Mon Jan 22 2001 Bill Nottingham <notting@redhat.com>
- do LVM setup through normal initscripts mechanisms
- ignore backup files in /etc/sysconfig/network-scripts
- lots of .po file updates

* Tue Jan  2 2001 Bill Nottingham <notting@redhat.com>
- initial i18n support - originally from Conectiva

* Mon Dec 11 2000 Bill Nottingham <notting@redhat.com>
- only load sound if persistent DMA buffers are necessary
- fix lots of bugs: #18619, #21187, #21283, #12097
- integrate MAXFAIL option for ppp-watch
- don't load keymaps/fonts on a serial console

* Tue Nov 21 2000 Karsten Hopp <karsten@redhat.de>
- changed hdparm section in rc.sysinit to allow different
  parameters for each disk (if needed) by copying 
  /etc/sysconfig/harddisks to /etc/sysconfig/harddiskhda (hdb,hdc..)
- fix RFE #20967

* Tue Oct 31 2000 Than Ngo <than@redhat.com>
- fix the adding default route if GATEWAY=0.0.0.0

* Tue Oct 10 2000 Nalin Dahyabhai <nalin@redhat.com>
- handle "gw x.x.x.x" as the last pair of flags in ifup-routes (#18804)
- fix top-level makefile install target
- make usernetctl just fall-through if getuid() == 0

* Sun Sep  3 2000 Florian La Roche <Florian.LaRoche@redhat.com>
- /etc/init.d is already provided by chkconfig

* Wed Aug 23 2000 Nalin Dahyabhai <nalin@redhat.com>
- set "holdoff ${RETRYTIMEOUT} ktune" for demand-dialed PPP links

* Tue Aug 22 2000 Bill Nottingham <notting@redhat.com>
- update documentation (#15475)

* Tue Aug 22 2000 Than Ngo <than@redhat.de>
- add KDE2 support to prefdm

* Mon Aug 21 2000 Bill Nottingham <notting@redhat.com>
- add usleep after kill -KILL in pidofproc, works around lockd issues (#14847)
- add some fallback logic to prefdm (#16464)

* Fri Aug 18 2000 Bill Nottingham <notting@redhat.com>
- don't load usb drivers if they're compiled statically
- don't call ifdown-post twice for ppp (#15285)

* Wed Aug 16 2000 Bill Nottingham <notting@redhat.com>
- fix /boot/kernel.h generation (#16236, #16250)

* Tue Aug 15 2000 Nalin Dahyabhai <nalin@redhat.com>
- be more careful about creating files in netreport (#16164)

* Sat Aug 11 2000 Nalin Dahyabhai <nalin@redhat.com>
- move documentation for the DEMAND and IDLETIMEOUT values to the right
  section of sysconfig.txt

* Wed Aug  9 2000 Bill Nottingham <notting@redhat.com>
- load agpgart if necessary (hack)
- fix /boot/kernel.h stuff (jakub)

* Mon Aug  7 2000 Bill Nottingham <notting@redhat.com>
- remove console-tools requirement
- in netfs, start portmap if needed
- cosmetic cleanups, minor tweaks
- don't probe USB controllers

* Mon Aug  7 2000 Nalin Dahyabhai <nalin@redhat.com>
- fix demand-dialing support for PPP devices
- change updetach back to nodetach

* Sun Aug  6 2000 Bill Nottingham <notting@redhat.com>
- add RETRYCONNECT option for ifcfg-pppX files (kenn@linux.ie)

* Wed Jul 26 2000 Bill Nottingham <notting@redhat.com>
- fix unclean shutdown

* Tue Jul 25 2000 Nalin Dahyabhai <nalin@redhat.com>
- s/nill/null/g

* Tue Jul 25 2000 Bill Nottingham <notting@redhat.com>
- unmount usb filesystem on halt
- run /sbin/ifup-pre-local if it exists

* Tue Jul 18 2000 Trond Eivind Glomsr�d <teg@redhat.com>
- add "nousb" command line parameter
- fix some warnings when mounting /proc/bus/usb

* Sat Jul 15 2000 Matt Wilson <msw@redhat.com>
- kill all the PreTransaction stuff
- directory ownership cleanups, add more LSB symlinks
- move all the stuff back in to /etc/rc.d/

* Thu Jul 13 2000 Bill Nottingham <notting@redhat.com>
- fix == tests in rc.sysinit
- more %pretrans tweaks

* Thu Jul 13 2000 Jeff Johnson <jbj@redhat.com>
- test if /etc/rc.d is a symlink already in pre-transaction syscalls.

* Tue Jul 11 2000 Bill Nottingham <notting@redhat.com>
- implement the %pre with RPM Magic(tm)

* Sat Jul  8 2000 Bill Nottingham <notting@redhat.com>
- fix it to not follow /etc/rc.d

* Fri Jul  7 2000 Bill Nottingham <notting@redhat.com>
- fix %pre, again

* Thu Jul  6 2000 Bill Nottingham <notting@redhat.com>
- tweak %pre back to a mv (rpm is fun!)
- do USB initialization before fsck, so keyboard works if it fails

* Mon Jul  3 2000 Bill Nottingham <notting@redhat.com>
- rebuild; allow 'fastboot' kernel command line option to skip fsck

* Mon Jul 03 2000 Nalin Dahyabhai <nalin@redhat.com>
- fix demand-dialing with PPP

* Sun Jul 02 2000 Trond Eivind Glomsr�d <teg@redhat.com>
- don't use tail

* Thu Jun 28 2000 Trond Eivind Glomsr�d <teg@redhat.com>
- add support for USB controllers and HID devices 
  (mice, keyboards)

* Tue Jun 27 2000 Trond Eivind Glomsr�d <teg@redhat.com>
- add support for EIDE optimization

* Mon Jun 26 2000 Bill Nottingham <notting@redhat.com>
- tweak %%pre

* Wed Jun 21 2000 Preston Brown <pbrown@redhat.com>
- noreplace for adjtime file

* Fri Jun 16 2000 Nalin Dahyabhai <nalin@redhat.com>
- ifup-ppp: add hooks for demand-dialing PPP
- functions: use basename of process when looking for its PID file

* Thu Jun 15 2000 Bill Nottingham <notting@redhat.com>
- move from /etc/rc.d/init.d -> /etc/init.d

* Tue Jun 13 2000 Bill Nottingham <notting@redhat.com>
- set soft limit, not hard, in daemon function
- /var/shm -> /dev/shm

* Thu Jun 08 2000 Preston Brown <pbrown@redhat.com>
- use dhcpcd if pump fails.
- use depmod -A (faster)

* Sun Jun  4 2000 Bernhard Rosenkraenzer <bero@redhat.com>
- add autologin support to prefdm

* Thu Jun  1 2000 Bill Nottingham <notting@redhat.com>
- random networking fixes (alias routes, others)
- conf.modules -> modules.conf

* Thu May 11 2000 Nalin Dahyabhai <nalin@redhat.com>
- fix incorrect grep invocation in rc.sysinit (bug #11267)

* Wed Apr 19 2000 Bill Nottingham <notting@redhat.com>
- fix lang.csh, again (oops)
- use /poweroff, /halt to determine whether to poweroff

* Thu Apr 14 2000 Bill Nottingham <notting@redhat.com>
- fix testing of RESOLV_MODS (which shouldn't be used anyways)

* Tue Apr 04 2000 Ngo Than <than@redhat.de>
- fix overwrite problem of resolv.conf on ippp/ppp/slip connections

* Mon Apr  3 2000 Bill Nottingham <notting@redhat.com>
- fix typo in functions file
- explicitly set --localtime when calling hwclock if necessary

* Fri Mar 31 2000 Bill Nottingham <notting@redhat.com>
- fix typo in /etc/rc.d/init.d/network that broke linuxconf (#10472)

* Mon Mar 27 2000 Bill Nottingham <notting@redhat.com>
- remove compatiblity chkconfig links
- run 'netfs stop' on 'network stop' if necessary

* Tue Mar 21 2000 Bernhard Rosenkraenzer <bero@redhat.com>
- Mount /var/shm if required (2.3.99, 2.4)

* Mon Mar 20 2000 Bill Nottingham <notting@redhat.com>
- don't create resolv.conf 0600
- don't run ps as much (speed issues)
- allow setting of MTU
- other minor fixes

* Sun Mar 19 2000 Bernhard Rosenkraenzer <bero@redhat.com>
- Start devfsd if installed and needed (Kernel 2.4...)

* Wed Mar  8 2000 Bill Nottingham <notting@redhat.com>
- check that network devices are up before bringing them down

* Wed Mar  8 2000 Jakub Jelinek <jakub@redhat.com>
- update sysconfig.txt

* Tue Mar  7 2000 Bill Nottingham <notting@redhat.com>
- rerun sysctl on network start (for restarts)

* Mon Feb 28 2000 Bill Nottingham <notting@redhat.com>
- don't read commented raid devices

* Mon Feb 21 2000 Bill Nottingham <notting@redhat.com>
- fix typo in resolv.conf munging

* Thu Feb 17 2000 Bill Nottingham <notting@redhat.com>
- sanitize repair prompt
- initial support for isdn-config stuff

* Mon Feb 14 2000 Nalin Dahyabhai <nalin@redhat.com>
- add which as a package dependency (bug #9416)

* Tue Feb  8 2000 Bill Nottingham <notting@redhat.com>
- fixes for sound module loading

* Mon Feb  7 2000 Nalin Dahyabhai <nalin@redhat.com>
- check that LC_ALL/LINGUAS and LANG are set before referencing them in lang.csh
- fix check for /var/*/news, work around for bug #9140

* Fri Feb  4 2000 Nalin Dahyabhai <nalin@redhat.com>
- fix bug #9102

* Fri Feb  4 2000 Bill Nottingham <notting@redhat.com>
- if LC_ALL/LINGUAS == LANG, don't set them

* Wed Feb  2 2000 Bill Nottingham <notting@redhat.com>
- fix problems with linuxconf static routes

* Tue Feb  1 2000 Nalin Dahyabhai <nalin@redhat.com>
- shvar cleaning
- fix wrong default route ip in network-functions

* Mon Jan 31 2000 Nalin Dahyabhai <nalin@redhat.com>
- attempt to restore default route if PPP takes it over
- man page fix for ipcalc
- shvar cleaning
- automate maintaining /boot/System.map symlinks

* Mon Jan 31 2000 Bill Nottingham <notting@redhat.com>
- fix hanging ppp-watch
- fix issues with cleaning of /var/{run,lock}

* Fri Jan 21 2000 Bill Nottingham <notting@redhat.com>
- fix pidof calls in pidofproc

* Wed Jan 19 2000 Bill Nottingham <notting@redhat.com>
- fix ifup-ipx, don't munge resolv.conf if $DNS1 is already in it

* Thu Jan 13 2000 Bill Nottingham <notting@redhat.com>
- link popt statically

* Mon Jan 10 2000 Bill Nottingham <notting@redhat.com>
- don't try to umount /loopfs

* Mon Dec 27 1999 Bill Nottingham <notting@redhat.com>
- switch to using sysctl

* Mon Dec 13 1999 Bill Nottingham <notting@redhat.com>
- umount /proc *after* trying to turn off raid

* Mon Dec 06 1999 Michael K. Johnson <johnsonm@redhat.com>
- improvements in clone device handling
- better signal handling in ppp-watch
- yet another attempt to fix those rare PAP/CHAP problems

* Sat Nov 28 1999 Bill Nottingham <notting@redhat.com>
- impressive. Three new features, three new bugs.

* Mon Nov 22 1999 Michael K. Johnson <johnsonm@redhat.com>
- fix more possible failed CHAP authentication (with chat scripts)
- fix ppp default route problem
- added ppp-watch man page, fixed usernetctl man page
- make ifup-ppp work again when called from netcfg and linuxconf
- try to keep ppp-watch from filling up logs by respawning pppd too fast
- handle all linuxconf-style alias files with linuxconf

* Mon Nov 22 1999 Bill Nottingham <notting@redhat.com>
- load mixer settings for monolithic sound
- man page for ppp-watch
- add ARP variable for ifup
- some i18n fixes

* Wed Nov 10 1999 Bill Nottingham <notting@redhat.com>
- control stop-a separately from sysrq

* Mon Nov 08 1999 Michael K. Johnson <johnsonm@redhat.com>
- fix some failed CHAP authentication
- fix extremely unlikely, but slightly possible kill-random-process
  bug in ppp-watch
- allow DNS{1,2} in any ifcfg-* file, not just PPP, and
  add nameserver entries, don't just replace them
- don't use /tmp/confirm, use /var/run/confirm instead

* Tue Nov  2 1999 Bill Nottingham <notting@redhat.com>
- fix lang.csh /tmp race oops

* Wed Oct 27 1999 Bill Nottingham <notting@redhat.com>
- we now ship hwclock on alpha.

* Mon Oct 25 1999 Jakub Jelinek <jakub@redhat.com>
- fix check for serial console, don't use -C argument to fsck
  on serial console.

* Mon Oct 18 1999 Bill Nottingham <notting@redhat.com>
- do something useful with linuxconf 'any' static routes.

* Tue Oct 12 1999 Matt Wilson <msw@redhat.com>
- added patch from Owen to source i18n configuration before starting prefdm

* Mon Oct 11 1999 Bill Nottingham <notting@redhat.com>
- support for linuxconf alias files
- add support for Jensen clocks.

* Tue Oct  5 1999 Bill Nottingham <notting@redhat.com>
- assorted brown paper bag fixes
- check for programs/files before executing/sourcing them
- control stop-a like magic sysrq

* Thu Sep 30 1999 Bill Nottingham <notting@redhat.com>
- req. e2fsprogs >= 1.15

* Fri Sep 24 1999 Bill Nottingham <notting@redhat.com>
- munge C locale definitions to en_US
- use fsck's completion bar

* Thu Sep 23 1999 Michael K. Johnson <johnsonm@redhat.com>
- ppp-watch now always kills pppd pgrp to make sure dialers are dead,
  and tries to hang up the modem

* Tue Sep 21 1999 Bill Nottingham <notting@redhat.com>
- add a DEFRAG_IPV4 option

* Mon Sep 20 1999 Michael K. Johnson <johnsonm@redhat.com>
- changed to more modern defaults for PPP connections

* Mon Sep 20 1999 Bill Nottingham <notting@redhat.com>
- kill processes for umount in halt, too.
- fixes to remove /usr dependencies

* Fri Sep 17 1999 Bill Nottingham <notting@redhat.com>
- load/save mixer settings in rc.sysinit, halt

* Mon Sep 13 1999 Michael K. Johnson <johnsonm@redhat.com>
- add --remotename option to wvdial code
- make sure we do not have an earlier version of wvdial that doesn't
  know how handle --remotename
- make ppp-watch background itself after 30 seconds even if
  connection does not come up, at boot time only, so that a
  non-functional PPP connection cannot hang boot.

* Sun Sep 12 1999 Bill Nottingham <notting@redhat.com>
- a couple of /bin/sh -> /bin/bash fixes
- fix swapoff silliness

* Fri Sep 10 1999 Bill Nottingham <notting@redhat.com>
- chkconfig --del in %preun, not %postun
- use killall5 in halt
- swapoff non-/etc/fstab swap

* Wed Sep 08 1999 Michael K. Johnson <johnsonm@redhat.com>
- ifdown now synchronous (modulo timeouts)
- several unrelated cleanups, primarily in ifdown

* Tue Sep  7 1999 Bill Nottingham <notting@redhat.com>
- add an 'unconfigure' sort of thing

* Mon Sep 06 1999 Michael K. Johnson <johnsonm@redhat.com>
- added ppp-watch to make "ifup ppp*" synchronous

* Fri Sep  3 1999 Bill Nottingham <notting@redhat.com>
- require lsof

* Wed Sep  1 1999 Bill Nottingham <notting@redhat.com>
- add interactive prompt

* Tue Aug 31 1999 Bill Nottingham <notting@redhat.com>
- disable magic sysrq by default

* Mon Aug 30 1999 Bill Nottingham <notting@redhat.com>
- new NFS unmounting from Bill Rugolsky <rugolsky@ead.dsa.com> 
- fix ifup-sl/dip confusion
- more raid startup cleanup
- make utmp group 22

* Fri Aug 20 1999 Bill Nottingham <notting@redhat.com>
- pass hostname to pump
- add lang.csh

* Thu Aug 19 1999 Bill Nottingham <notting@redhat.com>
- more wvdial updates
- fix a *stupid* bug in process reading

* Fri Aug 13 1999 Bill Nottingham <notting@redhat.com>
- add new /boot/kernel.h boot kernel version file
- new RAID startup

* Fri Aug 13 1999 Michael K. Johnson <johnsonm@redhat.com>
- use new linkname argument to pppd to make if{up,down}-ppp
  reliable -- requires ppp-2.3.9 or higher

* Mon Aug  2 1999 Bill Nottingham <notting@redhat.com>
- fix typo.
- add 'make check'

* Wed Jul 28 1999 Michael K. Johnson <johnsonm@redhat.com>
- simple wvdial support for ppp connections

* Mon Jul 26 1999 Bill Nottingham <notting@redhat.com>
- stability fixes for initlog
- initlog now has a config file
- add alias speedup from dharris@drh.net
- move netfs links
- usleep updates

* Thu Jul  8 1999 Bill Nottingham <notting@redhat.com>
- remove timeconfig dependency
- i18n fixes from nkbj@image.dk
- move inputrc to setup package

* Tue Jul  6 1999 Bill Nottingham <notting@redhat.com>
- fix killall links, some syntax errors

* Fri Jun 25 1999 Bill Nottingham <notting@redhat.com>
- don't make module-info, System.map links
- handle utmpx/wtmpx
- fix lots of bugs in 4.21 release :)

* Thu Jun 17 1999 Bill Nottingham <notting@redhat.com>
- set clock as soon as possible
- use INITLOG_ARGS everywhere
- other random fixes in networking

* Mon Jun 14 1999 Bill Nottingham <notting@redhat.com>
- oops, don't create /var/run/utmp and then remove it.
- stomp RAID bugs flat. Sort of.

* Mon May 24 1999 Bill Nottingham <notting@redhat.com>
- clean out /var better
- let everyone read /var/run/ppp*.dev
- fix network startup so it doesn't depend on /usr

* Tue May 11 1999 Bill Nottingham <notting@redhat.com>
- various fixes to rc.sysinit
- fix raid startup
- allow for multi-processor /etc/issues

* Sun Apr 18 1999 Matt Wilson <msw@redhat.com>
- fixed typo - "Determing" to "Determining"

* Fri Apr 16 1999 Preston Brown <pbrown@redhat.com>
- updated inputrc so that home/end/del work on console, not just X

* Thu Apr 08 1999 Bill Nottingham <notting@redhat.com>
- fix more logic in initlog
- fix for kernel versions in ifup-aliases
- log to /var/log/boot.log

* Wed Apr 07 1999 Bill Nottingham <notting@redhat.com>
- fix daemon() function so you can specify pid to look for

* Wed Apr 07 1999 Erik Troan <ewt@redhat.com>
- changed utmp,wtmp to be group writeable and owned by group utmp

* Tue Apr 06 1999 Bill Nottingham <notting@redhat.com>
- fix loading of consolefonts/keymaps
- three changelogs. three developers. one day. Woohoo!

* Tue Apr 06 1999 Michael K. Johnson <johnsonm@redhat.com>
- fixed ifup-ipx mix-up over . and _

* Tue Apr 06 1999 Erik Troan <ewt@redhat.com>
- run /sbin/ifup-local after bringing up an interface (if that file exists)

* Mon Apr  5 1999 Bill Nottingham <notting@redhat.com>
- load keymaps & console font early
- fixes for channel bonding, strange messages with non-boot network interfaces

* Sat Mar 27 1999 Cristian Gafton <gafton@redhat.com>
- added sysvinitfiles as a documenattaion file

* Fri Mar 26 1999 Bill Nottingham <notting@redhat.com>
- nfsfs -> netfs

* Mon Mar 22 1999 Bill Nottingham <notting@redhat.com>
- don't source /etc/sysconfig/init if $BOOTUP is already set

* Fri Mar 19 1999 Bill Nottingham <notting@redhat.com>
- don't run linuxconf if /usr isn't mounted
- set macaddr before bootp
- zero in the /var/run/utmpx file (gafton)
- don't set hostname on ppp/slip (kills X)
			
* Wed Mar 17 1999 Bill Nottingham <notting@redhat.com>
- exit ifup if pump fails
- fix stupid errors in reading commands from subprocess

* Tue Mar 16 1999 Bill Nottingham <notting@redhat.com>
- fix ROFS logging
- make fsck produce more happy output
- fix killproc logic

* Mon Mar 15 1999 Bill Nottingham <notting@redhat.com>
- doc updates
- support for SYSFONTACM, other console-tools stuff
- add net route for interface if it isn't there.
- fix for a bash/bash2 issue

* Mon Mar 15 1999 Michael K. Johnson <johnsonm@redhat.com>
- pam_console lockfile cleanup added to rc.sysinit

* Sun Mar 14 1999 Bill Nottingham <notting@redhat.com>
- fixes in functions for 'action'
- fixes for pump

* Wed Mar 10 1999 Bill Nottingham <notting@redhat.com>
- Mmm. Must always remove debugging code. before release. *thwap*
- pump support
- mount -a after mount -a -t nfs

* Thu Feb 25 1999 Bill Nottingham <notting@redhat.com>
- put preferred support back in

* Thu Feb 18 1999 Bill Nottingham <notting@redhat.com>
- fix single-user mode (source functions, close if)

* Wed Feb 10 1999 Bill Nottingham <notting@redhat.com>
- turn off xdm in runlevel 5 (now a separate service)

* Thu Feb  4 1999 Bill Nottingham <notting@redhat.com>
- bugfixes (ifup-ppp, kill -TERM, force fsck, hwclock --adjust, setsysfont)
- add initlog support. Now everything is logged (and bootup looks different)

* Thu Nov 12 1998 Preston Brown <pbrown@redhat.com>
- halt now passed the '-i' flag so that network interfaces disabled

* Tue Nov 10 1998 Michael K. Johnson <johnsonm@redhat.com>
- handle new linuxconf output for ipaliases

* Mon Oct 15 1998 Erik Troan <ewt@redhat.com>
- fixed raid start stuff
- added raidstop to halt

* Mon Oct 12 1998 Cristian Gafton <gafton@redhat.com>
- handle LC_ALL

* Mon Oct 12 1998 Preston Brown <pbrown@redhat.com>
- adjusted setsysfont to always run setfont, even if only w/default font

* Tue Oct 06 1998 Cristian Gafton <gafton@redhat.com>
- rc.sysvinit should be working with all kernel versions now
- requires e2fsprogs (for fsck)
- set INPUTRC and LESSCHARSET on linux-lat

* Wed Sep 16 1998 Jeff Johnson <jbj@redhat.com>
- /etc/rc.d/rc: don't run /etc/rc.d/rcN.d/[KS]??foo.{rpmsave,rpmorig} scripts.
- /etc/rc.d/rc.sysinit: raid startup (Nigel.Metheringham@theplanet.net).
- /sbin/setsysfont: permit unicode fonts.

* Mon Aug 17 1998 Erik Troan <ewt@redhat.com>
- don't add 'Red Hat Linux' to /etc/issue; use /etc/redhat-release as is

* Sun Aug 16 1998 Jeff Johnson <jbj@redhat.com>
- paranoia improvements to .rhkmvtag
- if psacct with /sbin/accton, than turn off accounting

* Tue Jul  7 1998 Jeff Johnson <jbj@redhat.com>
- start/stop run levels changed.
- ipx_configure/ipx_internal_net moved to /sbin.

* Wed Jul 01 1998 Erik Troan <ewt@redhat.com>
- usernetctl didn't understand "" around USERCTL attribute

* Wed Jul  1 1998 Jeff Johnson <jbj@redhat.com>
- Use /proc/version to find preferred modules.
- Numerous buglets fixed.

* Sun Jun 07 1998 Erik Troan <ewt@redhat.com> 
- rc.sysinit looks for bootfile= as well as BOOT_IMAGE to set 
  /lib/modules/preferred symlink

* Mon Jun 01 1998 Erik Troan <ewt@redhat.com>
- ipcalc should *never* have been setgid anything
- depmod isn't run properly for non-serial numbered kernels

* Wed May 06 1998 Donnie Barnes <djb@redhat.com>
- added system font and language setting

* Mon May 04 1998 Michael K. Johnson <johnsonm@redhat.com>
- Added missing files to packagelist.

* Sat May 02 1998 Michael K. Johnson <johnsonm@redhat.com>
- Added lots of linuxconf support.  Should still work on systems that
  do not have linuxconf installed, but linuxconf gives enhanced support.
- In concert with linuxconf, added IPX support.  Updated docs to reflect it.

* Fri May 01 1998 Erik Troan <ewt@redhat.com>
- rc.sysinit uses preferred directory

* Sun Apr 05 1998 Erik Troan <ewt@redhat.com>
- updated rc.sysinit to deal with kernel versions with release numbers

* Sun Mar 22 1998 Erik Troan <ewt@redhat.com>
- use ipcalc to calculate the netmask if one isn't specified

* Tue Mar 10 1998 Erik Troan <ewt@redhat.com>
- added and made use of ipcalc

* Tue Mar 10 1998 Erik Troan <ewt@redhat.com>
- removed unnecessary dhcp log from /tmp

* Mon Mar 09 1998 Erik Troan <ewt@redhat.com>
- if bootpc fails, take down the device

* Mon Mar 09 1998 Erik Troan <ewt@redhat.com>
- added check for mktemp failure

* Thu Feb 05 1998 Erik Troan <ewt@redhat.com>
- fixed support for user manageable cloned devices

* Mon Jan 12 1998 Michael K. Johnson <johnsonm@redhat.com>
- /sbin/ isn't always in $PATH, so call /sbin/route in ifup-routes

* Wed Dec 31 1997 Erik Troan <ewt@redhat.com>
- touch /var/lock/subsys/kerneld after cleaning out /var/lock/subsys
- the logic for when  /var/lock/subsys/kerneld is touched was backwards

* Tue Dec 30 1997 Erik Troan <ewt@redhat.com>
- tried to get /proc stuff right one more time (uses -t nonfs,proc now)
- added support for /fsckoptions
- changed 'yse' to 'yes' in KERNELD= line

* Tue Dec 09 1997 Erik Troan <ewt@redhat.com>
- set domainname to "" if none is specified in /etc/sysconfig/network
- fix /proc mounting to get it in /etc/mtab

* Mon Dec 08 1997 Michael K. Johnson <johnsonm@redhat.com>
- fixed inheritance for clone devices

* Fri Nov 07 1997 Erik Troan <ewt@redhat.com>
- added sound support to rc.sysinit

* Fri Nov 07 1997 Michael K. Johnson <johnsonm@redhat.com>
- Added missing "then" clause

* Thu Nov 06 1997 Michael K. Johnson <johnsonm@redhat.com>
- Fixed DEBUG option in ifup-ppp
- Fixed PPP persistance
- Only change IP forwarding if necessary

* Tue Oct 28 1997 Donnie Barnes <djb@redhat.com>
- removed the skeleton init script
- added the ability to 'nice' daemons

* Tue Oct 28 1997 Erik Troan <ewt@redhat.com>
- touch /var/lock/subsys/kerneld if it's running, and after mounting /var
- applied dhcp fix

* Thu Oct 23 1997 Donnie Barnes <djb@redhat.com>
- added status|restart to init scripts

* Thu Oct 23 1997 Michael K. Johnson <johnsonm@redhat.com>
- touch random seed file before chmod'ing it.

* Wed Oct 15 1997 Erik Troan <ewt@redhat.com>
- run domainname if NISDOMAIN is set 

* Wed Oct 15 1997 Michael K. Johnson <johnsonm@redhat.com>
- Make the random seed file mode 600.

* Tue Oct 14 1997 Michael K. Johnson <johnsonm@redhat.com>
- bring down ppp devices if ifdown-ppp is called while ifup-ppp is sleeping.

* Mon Oct 13 1997 Erik Troan <ewt@redhat.com>
- moved to new chkconfig conventions

* Sat Oct 11 1997 Erik Troan <ewt@redhat.com>
- fixed rc.sysinit for hwclock compatibility

* Thu Oct 09 1997 Erik Troan <ewt@redhat.com>
- run 'ulimit -c 0' before running scripts in daemon function

* Wed Oct 08 1997 Donnie Barnes <djb@redhat.com>
- added chkconfig support
- made all rc*.d symlinks have missingok flag

* Mon Oct 06 1997 Erik Troan <ewt@redhat.com>
- fixed network-scripts to allow full pathnames as config files
- removed some old 3.0.3 pcmcia device handling

* Wed Oct 01 1997 Michael K. Johnson <johnsonm@redhat.com>
- /var/run/netreport needs to be group-writable now that /sbin/netreport
  is setguid instead of setuid.

* Tue Sep 30 1997 Michael K. Johnson <johnsonm@redhat.com>
- Added network-functions to spec file.
- Added report functionality to usernetctl.
- Fixed bugs I introduced into usernetctl while adding clone device support.
- Clean up entire RPM_BUILD_ROOT directory in %clean.

* Mon Sep 29 1997 Michael K. Johnson <johnsonm@redhat.com>
- Clone device support in network scripts, rc scripts, and usernetctl.
- Disassociate from controlling tty in PPP and SLIP startup scripts,
  since they act as daemons.
- Spec file now provides start/stop symlinks, since they don't fit in
  the CVS archive.

* Tue Sep 23 1997 Donnie Barnes <djb@redhat.com>
- added mktemp support to ifup

* Thu Sep 18 1997 Donnie Barnes <djb@redhat.com>
- fixed some init.d/functions bugs for stopping httpd

* Tue Sep 16 1997 Donnie Barnes <djb@redhat.com>
- reworked status() to adjust for processes that change their argv[0] in
  the process table.  The process must still have it's "name" in the argv[0]
  string (ala sendmail: blah blah).

* Mon Sep 15 1997 Erik Troan <ewt@redhat.com>
- fixed bug in FORWARD_IPV4 support

* Sun Sep 14 1997 Erik Troan <ewt@redhat.com>
- added support for FORWARD_IPV4 variable

* Thu Sep 11 1997 Donald Barnes <djb@redhat.com>
- added status function to functions along with better killproc 
  handling.
- added /sbin/usleep binary (written by me) and man page
- changed BuildRoot to /var/tmp instead of /tmp

* Tue Jun 10 1997 Michael K. Johnson <johnsonm@redhat.com>
- /sbin/netreport sgid rather than suid.
- /var/run/netreport writable by group root.

- /etc/ppp/ip-{up|down} no longer exec their local versions, so
  now ifup-post and ifdown-post will be called even if ip-up.local
  and ip-down.local exist.

* Tue Jun 03 1997 Michael K. Johnson <johnsonm@redhat.com>
- Added missing -f to [ invocation in ksyms check.

* Fri May 23 1997 Michael K. Johnson <johnsonm@redhat.com>
- Support for net event notification:
  Call /sbin/netreport to request that SIGIO be sent to you whenever
  a network interface changes status (won't work for brining up SLIP
  devices).
  Call /sbin/netreport -r to remove the notification request.
- Added ifdown-post, and made all the ifdown scrips call it, and
  added /etc/ppp/ip-down script that calls /etc/ppp/ip-down.local
  if it exists, then calls ifdown-post.
- Moved ifup and ifdown to /sbin

* Tue Apr 15 1997 Michael K. Johnson <johnsonm@redhat.com>
- usernetctl put back in ifdown
- support for slaved interfaces

* Wed Apr 02 1997 Erik Troan <ewt@redhat.com>
- Created ifup-post from old ifup
- PPP, PLIP, and generic ifup use ifup-post

* Fri Mar 28 1997 Erik Troan <ewt@redhat.com>
- Added DHCP support
- Set hostname via reverse name lookup after configuring a networking
  device if the current hostname is (none) or localhost

* Tue Mar 18 1997 Erik Troan <ewt@redhat.com>
- Got rid of xargs dependency in halt script
- Don't mount /proc twice (unmount it in between)
- sulogin and filesystem unmounting only happened for a corrupt root 
  filesystem -- it now happens when other filesystems are corrupt as well

* Tue Mar 04 1997 Michael K. Johnson <johnsonm@redhat.com>
- PPP fixes and additions

* Mon Mar 03 1997 Erik Troan <ewt@redhat.com>
- Mount proc before trying to start kerneld so we can test for /proc/ksyms
  properly.

* Wed Feb 26 1997 Michael K. Johnson <johnsonm@redhat.com>
- Added MTU for PPP.
- Put PPPOPTIONS at the end of the options string instead of at the
  beginning so that they override other options.  Gives users more rope...
- Don't do module-based stuff on non-module systems.  Ignore errors if
  st module isn't there and we try to load it.

* Tue Feb 25 1997 Michael K. Johnson <johnsonm@redhat.com>
- Changed ifup-ppp and ifdown-ppp not to use doexec, because the argv[0]
  provided by doexec goes away when pppd gets swapped out.
- ifup-ppp now sets remotename to the logical name of the device.
  This will BREAK current PAP setups on netcfg-managed interfaces,
  but we needed to do this to add a reasonable interface-specific
  PAP editor to netcfg.

* Fri Feb 07 1997 Erik Troan <ewt@redhat.com>
- Added usernetctl wrapper for user mode ifup and ifdown's and man page
- Rewrote ppp and slip kill and retry code 
- Added doexec and man page
