from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Standby import TryQuitMainloop
from Screens.Console import Console
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, ConfigSelection, NoSave
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, pathExists, createDir, resolveFilename, SCOPE_CURRENT_SKIN
from os import system, listdir, remove as os_remove, rename as os_rename, stat as os_stat
from enigma import eTimer
import stat


class DeliteDevicesPanel(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = Label(_("Cancel"))
		self["key_yellow"] = Label(_("Mountpoints"))
		self["lab1"] = Label(_("Wait please while scanning your devices..."))
		
		self.list = []
		self["list"] = List(self.list)
		
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"back": self.close,
			"red": self.close,
			"yellow": self.mapSetup
		})
		
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updateList)
		self.gO()
	
	def gO(self):
		paths = ["/media/hdd","/media/usb","/media/downloads","/media/music","/media/personal","/media/photo","/media/video"]
		for path in paths:
			if not pathExists(path):
				createDir(path)
# hack !
		self.activityTimer.start(1)
		
	def updateList(self):
		self.activityTimer.stop()
		self.list = [ ]
		self.conflist = [ ]
		rc = system("blkid > /tmp/blkid.log")
		
		f = open("/tmp/blkid.log",'r')
		for line in f.readlines():
			if line.find('/dev/sd') == -1:
				continue
			parts = line.strip().split()
			device = parts[0][5:-2]
			partition = parts[0][5:-1]
			pos = line.find("UUID") + 6
			end = line.find('"', pos)
			uuid = line[pos:end]
			dtype = self.get_Dtype(device)
			category = dtype[0]
			png = LoadPixmap(dtype[1])
			size = self.get_Dsize(device, partition)
			model = self.get_Dmodel(device)
			mountpoint = self.get_Dpoint(uuid)
			name = "%s: %s" % (category, model)
			description = _(" device: %s  size: %s\n mountpoint: %s" % (parts[0], size, mountpoint))
			self.list.append((name, description, png))
			description = "%s  %s  %s" % (name, size, partition)
			self.conflist.append((description, uuid))
			
		self["list"].list = self.list
		self["lab1"].hide()
		os_remove("/tmp/blkid.log")
		
		
	def get_Dpoint(self, uuid):
		point = "NOT MAPPED"
		f = open("/etc/fstab",'r')
		for line in f.readlines():
			if line.find(uuid) != -1:
				parts = line.strip().split()
				point = parts[1]
				break
		f.close()
		return point
		
	def get_Dmodel(self, device):
		model = "Generic"
		filename = "/sys/block/%s/device/vendor" % (device)
		if fileExists(filename):
			vendor = file(filename).read().strip()
			filename = "/sys/block/%s/device/model" % (device)
			mod = file(filename).read().strip()
			model = "%s %s" % (vendor, mod)
		return model
		
	def get_Dsize(self, device, partition):
		size = "0"
		filename = "/sys/block/%s/%s/size" % (device, partition)
		if fileExists(filename):
			size = int(file(filename).read().strip())
			cap = size / 1000 * 512 / 1000
			size = "%d.%03d GB" % (cap/1000, cap%1000)
		return size
		
		
	def get_Dtype(self, device):
		pixpath = resolveFilename(SCOPE_CURRENT_SKIN, "")
		if pixpath == "/usr/share/enigma2/" or pixpath == "/usr/share/enigma2/./":
			pixpath = "/usr/share/enigma2/skin_default/"
		
		name = "USB"
		pix = pixpath + "icons/dev_usb.png"
		filename = "/sys/block/%s/removable" % (device)
		if fileExists(filename):
			if file(filename).read().strip() == "0":
				name = "HARD DISK"
				pix = pixpath + "icons/dev_hdd.png"
				
		return name, pix
		
		
	def mapSetup(self):
		self.session.openWithCallback(self.close, DeliteSetupDevicePanelConf, self.conflist)
						

class DeliteSetupDevicePanelConf(Screen, ConfigListScreen):
	def __init__(self, session, devices):
		Screen.__init__(self, session)
		
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["Linconn"] = Label(_("Wait please while scanning your box devices..."))
		
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"red": self.close,
			"green": self.savePoints,
			"back": self.close

		})
		
		self.devices = devices
		self.updateList()
	
	
	def updateList(self):
		self.list = []
		for device in self.devices:
			item = NoSave(ConfigSelection(default = "Not mapped", choices = self.get_Choices()))
			item.value = self.get_currentPoint(device[1])
			res = getConfigListEntry(device[0], item, device[1])
			self.list.append(res)
		
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self["Linconn"].hide()



	def get_currentPoint(self, uuid):
		point = "Not mapped"
		f = open("/etc/fstab",'r')
		for line in f.readlines():
			if line.find(uuid) != -1:
				parts = line.strip().split()
				point = parts[1].strip()
				break
		f.close()
		return point

	def get_Choices(self):
		choices = [("Not mapped", "Not mapped")]
		folders = listdir("/media")
		for f in folders:
			if f == "net":
				continue
			c = "/media/" + f
			choices.append((c,c))
		return choices
			
		

	def savePoints(self):
		f = open("/etc/fstab",'r')
		out = open("/etc/fstab.tmp", "w")
		for line in f.readlines():
			if line.find("UUID") != -1 or len(line) < 6:
				continue
			out.write(line)
		for x in self["config"].list:
			if x[1].value != "Not mapped":
				line = "UUID=%s    %s    auto   defaults    0  0\n" % (x[2], x[1].value)
				out.write(line)

		out.write("\n")
		f.close()
		out.close()
		os_rename("/etc/fstab.tmp", "/etc/fstab")
		message = _("Devices changes need a system restart to take effects.\nRestart your Box now?")
		self.session.openWithCallback(self.restBo, MessageBox, message, MessageBox.TYPE_YESNO)
			
	def restBo(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()
	
	
class BlackPoleSwap(Screen):
	skin = """
	<screen position="center,center" size="420,240" title="Black Hole Swap File Manager">
		<widget name="lab1" position="10,20" size="400,150" font="Regular;20" transparent="1"/>
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,190" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,190" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,190" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,190" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,190" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,190" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
	</screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["lab1"] = Label(_("Swap status: disabled"))
		self["key_red"] = Label(_("Close"))
		self["key_green"] = Label(_("Create"))
		self["key_yellow"] = Label(_("Remove"))
		
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"back": self.close,
			"red": self.close,
			"green": self.keyGreen,
			"yellow": self.keyYellow
		})

		self.onLayoutFinish.append(self.updateSwap)
		
	
	def updateSwap(self):
		self.swap_file = ""
		swapinfo = _("Swap status: disabled")
		f = open("/proc/swaps",'r')
 		for line in f.readlines():
			if line.find('swapfile') != -1:
				parts = line.split()
				self.swap_file = parts[0].strip()
				size = int(parts[2].strip()) / 1024
				swapinfo = _("Swap status: active\nSwap file: %s \nSwap size: %d M \nSwap used: %s Kb") % (self.swap_file, size, parts[3].strip())

		f.close()
		self["lab1"].setText(swapinfo)
		
		
	def keyYellow(self):
		if self.swap_file:
			cmd = "swapoff %s" % self.swap_file
			rc = system(cmd)
			try:
				out = open("/etc/init.d/bp_swap", "w")
				strview = "#!/bin/sh\n\nexit 0"
				out.write(strview)
				out.close()
				system("chmod 0755 /etc/init.d/bp_swap")
			except:
				pass
			self.updateSwap()
		else:
			self.session.open(MessageBox, _("Swap already disabled."), MessageBox.TYPE_INFO)	
	
	def keyGreen(self):
		if self.swap_file:
			self.session.open(MessageBox, _("Swap file is active.\nRemove it before to create a new swap space."), MessageBox.TYPE_INFO)
		else:
			options =[]
			f = open("/proc/mounts",'r')
			for line in f.readlines():
				if line.find('/media/sd') != -1:
					continue
				elif line.find('/media/') != -1:
					if line.find(' ext') != -1:
						parts = line.split()
						options.append([parts[1].strip(), parts[1].strip()])
			f.close()
			if len(options) == 0:
				self.session.open(MessageBox, _("Sorry no valid device found.\nBe sure your device is Linux formatted and mapped.\nPlease use Black Hole format wizard and Black Hole device manager to prepare and map your usb stick."), MessageBox.TYPE_INFO)
			else:
				self.session.openWithCallback(self.selectSize,ChoiceBox, title="Select the Swap File device:", list=options)
	

	def selectSize(self, device):
		if device:
			self.new_swap = device[1] + "/swapfile"
			options = [['16 MB', '16384'], ['32 MB', '32768'], ['64 MB', '65536'], ['128 MB', '131072'], ['256 MB', '262144'], ['512 MB', '524288'], ['1 GB', '1048576'], ['2 GB', '2097152']]		
			self.session.openWithCallback(self.swapOn,ChoiceBox, title=_("Select the Swap File Size:"), list=options)
			
		
	def swapOn(self, size):
		if size:
			cmd = "dd if=/dev/zero of=%s bs=1024 count=%s 2>/dev/null" % (self.new_swap, size[1])
			rc = system(cmd)
			if rc == 0:
				cmd = "mkswap %s" % (self.new_swap)
				rc = system(cmd)
				cmd = "swapon %s" % (self.new_swap)
				rc = system(cmd)
				out = open("/etc/init.d/bp_swap", "w")
				strview = "#!/bin/sh\nmkswap " + self.new_swap + "\nswapon " + self.new_swap + "\nexit 0"
				out.write(strview)
				out.close()
				system("chmod 0755 /etc/init.d/bp_swap")
				self.session.open(MessageBox, _("Swap File created."), MessageBox.TYPE_INFO)
				self.updateSwap()
			else:
				self.session.open(MessageBox, _("Swap File creation Failed. Check for available space."), MessageBox.TYPE_INFO)
			
			

