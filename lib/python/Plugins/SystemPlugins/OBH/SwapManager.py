from os import system, stat as mystat, path, remove
from glob import glob
import stat
import re

from enigma import eTimer

from Components.config import config, configfile, ConfigSubsection, ConfigYesNo
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Harddisk import harddiskmanager, getProcMounts, bytesToHumanReadable, getSwapSizeChoices
from shlex import quote
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

config.swapmanager = ConfigSubsection()
config.swapmanager.swapautostart = ConfigYesNo(default=False)

# start: temp code - used due to config variable change
config.obhsettings.swapautostart = ConfigYesNo(default=False)
if config.obhsettings.swapautostart.value:
	config.swapmanager.swapautostart.value = True
	# switch off so doesn't happen on any subsuquent run
	config.obhsettings.swapautostart.value = False
	config.obhsettings.swapautostart.save()
# end: temp code
startswap = None


def partedSizeToHumanReadable(size):
	# parted's plain kB/MB/GB values are decimal, unlike /proc/swaps.
	match = re.fullmatch(r"(\d+(?:\.\d+)?)(B|kB|MB|GB|TB|KiB|MiB|GiB|TiB)", size)
	if match:
		unit = match.group(2)
		base = 1024 if "iB" in unit else 1000
		power = {"B": 0, "kB": 1, "MB": 2, "GB": 3, "TB": 4, "KiB": 1, "MiB": 2, "GiB": 3, "TiB": 4}[unit]
		return bytesToHumanReadable(float(match.group(1)) * base ** power)
	return size


def readActiveSwaps():
	"""The devices and files of the swaps in use (/proc/swaps), each as (name, type)."""
	try:
		with open("/proc/swaps") as f:
			return [(parts[0], parts[1]) for parts in (line.split() for line in f.readlines()[1:]) if len(parts) > 1]
	except OSError:
		return []


def swapPartitionMB(device):
	"""The size of a partition in MB, from its number of 512 byte sectors in /sys (0 if unknown)."""
	try:
		with open("/sys/class/block/%s/size" % path.basename(device)) as f:
			return int(f.read()) * 512 // 1000000
	except (OSError, ValueError):
		return 0


def swapPartitions(blkid):
	"""Return disk and eMMC swap partitions from blkid, excluding zram."""
	disks, mmc = [], []
	for line in (blkid or "").splitlines():
		match = re.match(r'(/dev/[^:\s]+):.*\bTYPE="swap"', line)
		if not match or "/zram" in match.group(1):
			continue
		label = re.search(r'\bPARTLABEL="([^"]*)"', line)
		(mmc if "/mmcblk" in match.group(1) else disks).append((match.group(1), label.group(1) if label else ""))
	return disks, mmc


def partitionName(device, label):
	"""Format a swap partition with its optional partition label."""
	return "%s: %s" % (device, label) if label else device


def swapFiles():
	"""Find swap files at the top of mounted local devices."""
	files = []
	for p in harddiskmanager.getMountedPartitions():
		d = path.normpath(p.mountpoint)
		if path.exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith(("/media/net/", "/media/autofs/")):
			files.extend(filename for filename in glob(d + "/swap*") if path.exists(filename))
	return files


def SwapAutostart(reason, session=None, **kwargs):
	global startswap
	if reason == 0:
		print("[SwapManager] autostart", config.swapmanager.swapautostart.value)
		if config.swapmanager.swapautostart.value:
			print("[SwapManager] autostart")
			startswap = StartSwap()
			startswap.start()


class StartSwap:
	def __init__(self):
		self.Console = Console()

	def start(self):
		self.Console.ePopen("/sbin/blkid", self.startSwap2)

	def startSwap2(self, result=None, retval=None, extra_args=None):
		disks, mmc = swapPartitions(result)
		files = swapFiles()
		swap_Fname = files[-1] if files else ""
		activeNames = [name for name, _type in readActiveSwaps()]
		print("[SwapManager][StartSwap] swap partitions of disks", disks, "eMMC", mmc, "swap file", swap_Fname)
		if disks:
			if swap_Fname:
				print("[SwapManager][StartSwap] SWAP file %s not switched on: the SWAP partition %s is used" % (swap_Fname, disks[0][0]))
			return
		if swap_Fname and swap_Fname not in activeNames:
			system("swapon -p 10 " + quote(swap_Fname))
			print("[SwapManager][StartSwap] SWAP file active on ", swap_Fname)
		if mmc and swap_Fname:
			print("[SwapManager][StartSwap] SWAP file %s chosen before swap partition on %s by priority" % (swap_Fname, mmc[0][0]))


class OpenBhSwap(Screen):
	skin = ["""
	<screen name="OpenBhSwap" position="center,center" size="%d,%d">
		<panel name="__DynamicColorButtonTemplate__"/>
		<widget name="autostart_off" position="%d,%d" zPosition="1" pixmap="skin_default/icons/lock_off.png" size="%d,%d" alphatest="blend" scale="1"/>
		<widget name="autostart_on" position="%d,%d" zPosition="2" pixmap="skin_default/icons/lock_on.png" size="%d,%d" alphatest="blend" scale="1"/>
		<widget name="lab1" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" transparent="1"/>
		<widget name="lab2" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" transparent="1"/>
		<widget name="lab3" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" transparent="1"/>
		<widget name="lab4" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" transparent="1" />
		<widget name="labplace" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" backgroundColor="#4D5375"/>
		<widget name="labsize" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" backgroundColor="#4D5375"/>
		<widget name="inactive" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" halign="center" backgroundColor="red"/>
		<widget name="active" position="%d,%d" size="%d,%d" font="Regular;%d" valign="center" halign="center" backgroundColor="green"/>
	</screen>""",
		560, 250,  # screen
		10, 50, 32, 32,  # lock off
		10, 50, 32, 32,  # lock on
		50, 50, 360, 30, 20,
		10, 100, 150, 30, 20,
		10, 150, 150, 30, 20,
		10, 200, 150, 30, 20,
		160, 100, 380, 30, 20,  # enough width for multiple swap partitions
		160, 150, 220, 30, 20,
		160, 200, 100, 30, 20,
		160, 200, 100, 30, 20,
				]  # noqa: E124

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("SWAP manager"))

		self["lab1"] = Label()
		self["autostart_on"] = Pixmap()
		self["autostart_off"] = Pixmap()
		self["lab2"] = Label(_("SWAP name:"))
		self["labplace"] = Label()
		self["lab3"] = Label(_("SWAP size:"))
		self["labsize"] = Label()
		self["lab4"] = Label(_("Status:"))
		self["inactive"] = Label(_("Inactive"))
		self["active"] = Label(_("Active"))
		self["key_red"] = Label(_("Close"))
		self["key_green"] = Label(_("Activate"))
		self["key_yellow"] = Label(_("Enable Autostart"))
		self["key_blue"] = Label(_("Create"))
		self["swapname_summary"] = StaticText()
		self["swapactive_summary"] = StaticText()
		self.Console = Console()
		self.swap_name = ""
		self.new_name = ""
		self.creatingswap = False
		self.swap_active = False
		self.swap_Pactive = False
		self.diskSwaps = []
		self.inactiveDiskSwaps = []
		self["actions"] = ActionMap(["WizardActions", "ColorActions", "MenuActions"],
		{
			"back": self.close,
			"red": self.close,
			"green": self.actDeact,
			"yellow": self.autoSsWap,
			"blue": self.createDel,
			"menu": self.close,
		})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.getSwapDevice)
		self.updateSwap()

	def updateSwap(self, result=None, retval=None, extra_args=None):
		self["actions"].setEnabled(False)
		self.swap_active = False
		self.swap_name = None
		self["autostart_on"].hide()
		self["autostart_off"].show()
		self["active"].hide()
		self["inactive"].show()
		self["labplace"].hide()
		self["labsize"].hide()
		self["swapactive_summary"].setText(_("Current status:"))
		scanning = _("Wait please while scanning...")
		self["lab1"].setText(scanning)
		self.activityTimer.start(10)

	def getSwapDevice(self):
		self.activityTimer.stop()
		if path.exists("/etc/rcS.d/S98SwapManager"):
			remove("/etc/rcS.d/S98SwapManager")
			config.swapmanager.swapautostart.value = True
			config.swapmanager.swapautostart.save()
		if path.exists("/tmp/swapdevices.tmp"):
			remove("/tmp/swapdevices.tmp")
		self.Console.ePopen("/sbin/blkid", self.updateSwap2)

	def updateSwap2(self, result=None, retval=None, extra_args=None):
		self.swap_active = False
		self.swap_Pname = ""
		self.Pswapsize = 0
		self.swap_Pactive = False
		self.swap_Fname = ""
		self.Fswapsize = 0
		self.swap_Factive = False
		self.MMCdevice = False
		self.swapdevice = 0
		self.swapcount = 0
		self.swapsize = 0
		scanning = _("No SWAP found")
		activeSwaps = readActiveSwaps()
		activeNames = [name for name, _type in activeSwaps]
		disks, mmc = swapPartitions(result)
		self.diskSwaps = [device for device, _label in disks]
		self.inactiveDiskSwaps = [device for device in self.diskSwaps if device not in activeNames]
		self.swap_Pactive = len(self.inactiveDiskSwaps) < len(self.diskSwaps)
		labels = dict(disks + mmc)
		if not self.diskSwaps:
			for device, _label in mmc:
				if device not in activeNames:
					self.swap_Pname = device
			for name, swapType in activeSwaps:
				if swapType == "partition" and "mmc" in name:
					self.MMCdevice = True
					self.swap_Pname = name
					self.swap_name = _("manufacturer defined swap")
			if self.swap_Pname:
				self.Pswapsize = "%d MB" % swapPartitionMB(self.swap_Pname)
		else:
			self.Pswapsize = "%d MB" % sum(swapPartitionMB(device) for device in self.diskSwaps)
		print("[SwapManager][updateSwap2] disks:%s inactive:%s partition:%s size:%s" % (self.diskSwaps, self.inactiveDiskSwaps, self.swap_Pname, self.Pswapsize))

		self["key_blue"].setText(_("Create"))
		for filename in swapFiles():
			self.swap_name = self.swap_Fname = filename
			self["key_blue"].setText(_("Delete"))
			info = mystat(self.swap_name)
			self.Fswapsize = info[stat.ST_SIZE]

		if self.diskSwaps:
			self["labplace"].setText(", ".join(partitionName(device, labels[device]) for device in self.diskSwaps))
		elif self.swap_Fname:
			self["labplace"].setText(self.swap_Fname)
			self["autostart_on"].hide()
			self["autostart_off"].show()
		elif self.swap_Pname:
			self["labplace"].setText(partitionName(self.swap_Pname, labels.get(self.swap_Pname, "")))
		else:
			self["labplace"].setText("")
		self["labplace"].show()

		for name, swapType in activeSwaps:
			if swapType == "file":
				self["autostart_on"].show()
				self["autostart_off"].hide()
				self.swap_active = self.swap_Factive = True
			elif name == self.swap_Pname and not self.swap_Fname:
				self.swap_active = True
		if self.swap_Pactive:
			self.swap_active = True

		if self.diskSwaps:
			self.swapsize = self.Pswapsize
		elif self.swap_Fname:
			self.swapsize = bytesToHumanReadable(self.Fswapsize) if self.Fswapsize > 0 else ""
		elif self.swap_Pname:
			self.swapsize = self.Pswapsize
		self["labsize"].setText(self.swapsize)
		self["labsize"].show()

		if self.swap_Fname or self.swap_Pname or self.diskSwaps:
			if self.swap_active:
				self["inactive"].hide()
				self["active"].show()
				self["key_green"].setText(_("Deactivate"))
				self["swapactive_summary"].setText(_("Current status:") + " " + _("Active"))
			else:
				self["inactive"].show()
				self["active"].hide()
				self["key_green"].setText(_("Activate"))
				self["swapactive_summary"].setText(_("Current status:") + " " + _("Inactive"))
			if self.diskSwaps:
				scanning = _("SWAP partition enabled at startup")
				self["autostart_off"].hide()
				self["autostart_on"].show()
				self["key_green"].setText(_("Activate") if self.inactiveDiskSwaps else "")
				self["key_yellow"].setText("")
				if not self.swap_Fname:
					self["key_blue"].setText("")
			else:
				if self.swap_name == _("manufacturer defined swap"):
					self["key_green"].setText("")
					scanning = _("manufacturer defined swap enabled at startup")
				else:
					scanning = _("Enable SWAP at startup")
				if self.swap_name == _("manufacturer defined swap"):
					self["autostart_off"].hide()
					self["autostart_on"].show()
					self["key_yellow"].setText("")
				elif config.swapmanager.swapautostart.value:
					self["autostart_off"].hide()
					self["autostart_on"].show()
					self["key_yellow"].setText(_("Disable Autostart"))
				else:
					config.swapmanager.swapautostart.setValue(False)
					config.swapmanager.swapautostart.save()
					configfile.save()
					self["autostart_on"].hide()
					self["autostart_off"].show()
					self["key_yellow"].setText(_("Enable Autostart"))
			self["lab1"].setText(scanning)
			self["lab1"].show()
			self["actions"].setEnabled(True)
			self["swapname_summary"].setText(self["labplace"].text)
		else:
			self["lab1"].setText(scanning)
			self["lab1"].show()
			self["actions"].setEnabled(True)

	def actDeact(self):
		if self.diskSwaps:
			if self.inactiveDiskSwaps:
				self.Console.ePopen("; ".join("swapon " + quote(device) for device in self.inactiveDiskSwaps), self.updateSwap)
			return
		if self.swap_name == _("manufacturer defined swap"):
			return
		if self.swap_Factive:
			self.Console.ePopen("swapoff " + self.swap_Fname, self.updateSwap)
			self.swap_Factive = False
		else:
			if self.swap_Fname:
				self.Console.ePopen("swapon -p 10 " + self.swap_Fname, self.updateSwap)
				self.swap_Factive = True
				config.swapmanager.swapautostart.setValue(True)
				config.swapmanager.swapautostart.save()
				configfile.save()
			else:
				mybox = self.session.open(MessageBox, _("SWAP file not found. You have to create the file before you try to activate it."), MessageBox.TYPE_INFO)
				mybox.setTitle(_("Info"))
		self.updateSwap()

	def createDel(self):
		if self.diskSwaps and not self.swap_Fname:
			return
		if self.swap_Fname:
			if self.swap_Factive:
				self.Console.ePopen("swapoff " + self.swap_Fname, self.createDel2)
			else:
				self.createDel2(None, 0)
		else:
			self.doCreateSwap()

	def createDel2(self, result, retval, extra_args=None):
		if retval == 0:
			# print("[SwapManager][createDel2] delete swap = ", self.swap_Fname)
			self.Console.ePopen("rm " + self.swap_Fname, self.createDel3)

	def createDel3(self, result, retval, extra_args=None):
		print("[SwapManager][createDel3] delete swap, retval, result", retval, "   ", result)
		if config.swapmanager.swapautostart.value:
			config.swapmanager.swapautostart.setValue(False)
			config.swapmanager.swapautostart.save()
			configfile.save()
		self.updateSwap()

	def doCreateSwap(self):
		supported_filesystems = frozenset(("ext4", "ext3"))
		candidates = []
		mounts = getProcMounts()
		for partition in harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if len(candidates):
			self.session.openWithCallback(self.doCSname, ChoiceBox, title=_("Please select device to use as SWAP file location."), list=candidates)
		else:
			self.session.open(MessageBox, _("Sorry, no physical devices that supports SWAP attached. Can't create SWAP file on network or fat32 file-systems."), MessageBox.TYPE_INFO, timeout=10)

	def doCSname(self, name):
		if name:
			self.new_name = name[1]
			myoptions = getSwapSizeChoices((8, 16, 32, 64, 96, 128, 256, 512, 756, 1024))
			self.session.openWithCallback(self.doCSsize, ChoiceBox, title=_("Select the SWAP file size:"), list=myoptions)

	def doCSsize(self, swapsize):
		if swapsize:
			myfile = path.join(self.new_name, "swapfile")
			if path.lexists(myfile):
				self.session.open(MessageBox, _("A swapfile already exists at this location. It will not be overwritten."), MessageBox.TYPE_INFO)
				return
			self["actions"].setEnabled(False)
			scanning = _("Wait please while creating SWAP file...")
			self["lab1"].setText(scanning)
			self["lab1"].show()
			size_megabytes, base = swapsize[1]
			self.commands = []
			self.commands.append("dd if=/dev/zero of=%s bs=%d count=%d 2>/dev/null" % (quote(myfile), base, size_megabytes * base))
			self.commands.append("mkswap " + quote(myfile))
			self.commands.append("swapon -p 10 " + myfile)  # activate the new swap file straight away, as actDeact() does
			config.swapmanager.swapautostart.setValue(True)
			config.swapmanager.swapautostart.save()
			configfile.save()
			self.Console.eBatch(self.commands, self.updateSwap, debug=True)

	def autoSsWap(self):
		if self.diskSwaps or self.swap_name == _("manufacturer defined swap"):
			return
		if self.swap_name:
			if config.swapmanager.swapautostart.value:
				config.swapmanager.swapautostart.setValue(False)
				config.swapmanager.swapautostart.save()
			else:
				config.swapmanager.swapautostart.setValue(True)
				config.swapmanager.swapautostart.save()
			configfile.save()
		else:
			mybox = self.session.open(MessageBox, _("You have to create a SWAP file before trying to activate the autostart."), MessageBox.TYPE_INFO)
			mybox.setTitle(_("Info"))
		self.updateSwap()
