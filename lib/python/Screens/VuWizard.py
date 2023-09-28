import glob
from boxbranding import getBoxType, getMachineMtdKernel, getMachineMtdRoot
from Components.config import config, configfile
from Components.Console import Console
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Screens.MessageBox import MessageBox
from Screens.Rc import Rc
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import fileExists, pathExists, resolveFilename, SCOPE_SKIN


patterns = [
	"plugin-systemplugins",
	"plugin-extensions",
	"packagegroup-base-alsa",
	"packagegroup-base-bluetooth",
	"packagegroup-base-smbfs",
	"packagegroup-base-smbfs-client",
	"packagegroup-base-smbfs-server",
	"python3-pyasn1",
	"python3-pyasn1-modules",
	"python3-cryptography",
	"python3-future",
	"python3-mime",
	"alsa",
	"curl",
	"dvbsnoop",
	"firmware",
	"glibc",
	"gnome-themes",
	"hddtmp",
	"inadyn-mt",
	"kernel-module",
	"libcrypto-compat-0.9.7",
	"lib-samba",
	"lib-smb",
	"mime",
	"rtmpdump",
	"samba4",
	"webkit",
	"wpa-supplicant",
]

patterns_locale = [
	"enigma2-locale",
]

STARTUP = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % getMachineMtdRoot()					# /STARTUP
STARTUP_RECOVERY = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % getMachineMtdRoot() 			# /STARTUP_RECOVERY
STARTUP_1 = "kernel=/linuxrootfs1/zImage root=/dev/%s rootsubdir=linuxrootfs1" % getMachineMtdRoot() 	# /STARTUP_1
STARTUP_2 = "kernel=/linuxrootfs2/zImage root=/dev/%s rootsubdir=linuxrootfs2" % getMachineMtdRoot() 	# /STARTUP_2
STARTUP_3 = "kernel=/linuxrootfs3/zImage root=/dev/%s rootsubdir=linuxrootfs3" % getMachineMtdRoot() 	# /STARTUP_3


class VuWizard(WizardLanguage, Rc):
	def __init__(self, session, interface=None):
		self.xmlfile = resolveFilename(SCOPE_SKIN, "vuwizard.xml")
		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		Rc.__init__(self)
		self.skinName = ["VuWizard", "StartWizard"]
		self.session = session
		self.Console = Console(binary=True)
		self.ConsoleS = Console()
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.NextStep = None
		self.Text = None
		config.misc.Vuwizardenabled.value = False
		config.misc.Vuwizardenabled.save()
		if self.welcomeWarning not in self.onShow:
			self.onShow.append(self.welcomeWarning)

	def welcomeWarning(self):
		if self.welcomeWarning in self.onShow:
			self.onShow.remove(self.welcomeWarning)
		popup = self.session.openWithCallback(self.welcomeAction, MessageBox, _("Welcome to OpenBh!\n\n"
			"Select 'Standard' to setup Standard Vu+ image.\n\n"
			"Select 'Multiboot' to setup Vu+ Multiboot."), type=MessageBox.TYPE_YESNO, timeout=-1,
			default=False, list=[(_("Standard"), False), (_("Multiboot"), True)])
		popup.setTitle(_("Vu+ 4K image install options"))

	def welcomeAction(self, answer):
		print("[VuWizard][welcomeAction] answer", answer)
		if answer:
			print("[VuWizard][welcomeAction] arrived")
			if fileExists("/STARTUP_RECOVERY") or fileExists("/boot/STARTUP_RECOVERY"):
				self.close
			else:
				with open("/STARTUP", 'w') as f:
					f.write(STARTUP)
				with open("/STARTUP_RECOVERY", 'w') as f:
					f.write(STARTUP_RECOVERY)
				with open("/STARTUP_1", 'w') as f:
					f.write(STARTUP_1)
				with open("/STARTUP_2", 'w') as f:
					f.write(STARTUP_2)
				with open("/STARTUP_3", 'w') as f:
					f.write(STARTUP_3)
				cmdlist = []
				cmdlist.append("dd if=/dev/%s of=/zImage" % getMachineMtdKernel())					# backup old kernel
				cmdlist.append("dd if=/usr/bin/kernel_auto.bin of=/dev/%s" % getMachineMtdKernel())  # create new kernel
				cmdlist.append("mv /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")						# copy userroot routine
				for file in glob.glob("/media/*/vuplus/*/force.update", recursive=True):
					cmdlist.append("mv %s %s" % (file, file.replace("force.update", "noforce.update")))						# remove Vu force update(Vu+ Zero4k)
				hddExt4 = False
				if pathExists("/media/hdd"):
					with open("/proc/mounts", "r") as fd:
						xlines = fd.readlines()
						for xline in xlines:
							if xline.find("/media/hdd") != -1 and "ext4" in xline:
								hddExt4 = True
								break
				if hddExt4 and pathExists("/media/hdd/%s/linuxrootfs1" % getBoxType()):
					self.Console.eBatch(cmdlist, self.eMMCload, debug=True)
				elif hddExt4:
					if not pathExists("/media/hdd/%s" % getBoxType()):
						cmdlist.append("mkdir /media/hdd/%s" % getBoxType())
					cmdlist.append("mkdir /tmp/mmc")
					cmdlist.append("mount /dev/%s /tmp/mmc" % getMachineMtdRoot())
					cmdlist.append("rsync -aAXHS /tmp/mmc/ /media/hdd/%s/linuxrootfs1" % getBoxType())
					cmdlist.append("umount /tmp/mmc")
					cmdlist.append("cp /zImage /media/hdd/%s/linuxrootfs1/" % getBoxType())
					self.Console.eBatch(cmdlist, self.eMMCload, debug=True)
				else:
					cmdlist.append("mkdir /tmp/mmc")
					cmdlist.append("mkdir /linuxrootfs1")
					cmdlist.append("mount /dev/%s /tmp/mmc" % getMachineMtdRoot())
					cmdlist.append("/bin/tar -jcf /tmp/linuxrootfs1.tar.bz2 -C /tmp/mmc --exclude ./var/nmbd --exclude ./.resizerootfs --exclude ./linuxrootfs* --exclude ./.resize-rootfs --exclude ./.resize-linuxrootfs --exclude ./.resize-userdata --exclude ./var/lib/samba/private/msg.sock .")
					cmdlist.append("/bin/tar -jxf /tmp/linuxrootfs1.tar.bz2 -C /linuxrootfs1 .")
					cmdlist.append("cp /zimage /linuxrootfs1/")
					cmdlist.append("umount /tmp/mmc")
					self.Console.eBatch(cmdlist, self.reBoot, debug=True)
		else:
			self.close()

	def eMMCload(self, *args, **kwargs):
		cmdlist = []
		for eMMCslot in range(1, 4):
			if pathExists("/media/hdd/%s/linuxrootfs%s" % (getBoxType(), eMMCslot)):
				cmdlist.append("cp -R /media/hdd/%s/linuxrootfs%s . /" % (getBoxType(), eMMCslot))
				cmdlist.append("rm -r /media/hdd/%s/linuxrootfs%s" % (getBoxType(), eMMCslot))
		if cmdlist:
			cmdlist.append("rm -rf /media/hdd/%s" % getBoxType())
			self.Console.eBatch(cmdlist, self.reBoot, debug=False)
		else:
			self.reBoot()

	def reBoot(self, *args, **kwargs):
		with open("/STARTUP", 'w') as f:
			f.write(STARTUP_1)
		config.misc.restorewizardrun.value = True
		config.misc.restorewizardrun.save()
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()
		self.ConsoleS.ePopen("/usr/bin/opkg list_installed", self.readOpkg)

	def readOpkg(self, result, retval, extra_args):
		# print("[VuWizard] retval, result", retval, "   ", result)
		if result:
			cmdlist = []
			opkg_installed_list = result.split("\n")										# python list installed elements
			# print("[VuWizard] opkg_installed_list", opkg_installed_list)
			for opkg_element in opkg_installed_list:										# element e.g. opkg_status aio-grab - 1.0+git116+30847a1-r0
				if bool([x for x in patterns if x in opkg_element]):
					parts = opkg_element.strip().split()
					# print("[VuWizard]1 parts, parts0", parts, "   ", parts[0])
					cmdlist.append("/usr/bin/opkg remove --autoremove --add-dest /:/ " + parts[0] + " --force-remove --force-depends")
					continue
				if bool([x for x in patterns_locale if x in opkg_element]):
					if "en-gb" in opkg_element or "meta" in opkg_element:		# en-gb for OpenBh default - ensure don't clear .po
						continue
					parts = opkg_element.strip().split()
					# print("[VuWizard]2 parts, parts0", parts, "   ", parts[0])
					cmdlist.append("/usr/bin/opkg remove --autoremove --add-dest /:/ " + parts[0] + " --force-remove --force-depends")
					continue
					# print("[VuWizard] cmdlist", cmdlist)
			if cmdlist:
				cmdlist.append("rm -f /usr/share/fonts/wqy-microhei.ttc")
				self.Console.eBatch(cmdlist, self.bootSlot, debug=False)
		else:
			self.bootSlot()

	def bootSlot(self, *args, **kwargs):
		self.Console.ePopen("killall -9 enigma2 && init 6")
