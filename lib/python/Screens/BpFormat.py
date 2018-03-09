# Black Hole usb format utility coded by meo.

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.Console import Console
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
from os import system, listdir, remove as os_remove


class Bp_UsbFormat(Screen):
	skin = """
	<screen position="center,center" size="580,350" title="Black Hole Usb Format Wizard">
		<widget name="lab1" position="10,10" size="560,280" font="Regular;20" valign="top" transparent="1"/>
		<ePixmap pixmap="skin_default/buttons/red.png" position="100,300" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="340,300" size="140,40" alphatest="on" />
		<widget name="key_red" position="100,300" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="340,300" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		
		msg = _("This wizard will help you to format Usb mass storage devices for Linux.\n")
		msg += _("Please make sure your usb drive is NOT CONNECTED to your Vu+ box before you continue.\n")
		msg += _("If your usb drive is connected and mounted you must poweroff your box, remove the usb device and reboot.\n")
		msg += _("Press Green button to continue, when you are ready if your usb is disconnected.\n")

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Continue ->"))
		self["lab1"] = Label(msg)

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"back": self.checkClose,
			"red": self.checkClose,
			"green": self.step_Bump
		})
		self.step = 1
		self.devices = []
		self.device = None
		self.totalpartitions = 1
		self.totalsize = self.p1size = self.p2size = self.p3size = self.p4size = "0"
		self.canclose = True
	
	
	def stepOne(self):
		msg = _("Connect your usb storage to your Vu+ box\n")
		msg += _("Press Green button to continue when ready.\n\n")
		msg += _("Warning: If your usb is already connected\n")
		msg += _("to the box you have to unplug it, press\n")
		msg += _("the Red button and restart the wizard.\n")

		rc = system("/etc/init.d/autofs stop")
		self.devices = self.get_Devicelist()
		self["lab1"].setText(msg)
		self.step = 2
		
	def stepTwo(self):
		msg = _("The wizard will now try to identify your connected usb device. ")
		msg += _("Press Green button to continue.")
				
		self["lab1"].setText(msg)
		self.step = 3
	
	def stepThree(self):
		newdevices = self.get_Devicelist()
		for d in newdevices:
			if d not in self.devices:
				self.device = d
		if self.device is None:
			self.wizClose(_("Sorry, no new usb storage device detected.\nBe sure to follow the wizard instructions."))
		else:
			msg = self.get_Deviceinfo(self.device)
			self["lab1"].setText(msg)
			self.step = 4
			
	def stepFour(self):
		myoptions = [['1', '1'], ['2', '2'], ['3', '3'], ['4', '4']]
		self.session.openWithCallback(self.partSize1,ChoiceBox, title=_("Select number of partitions:"), list=myoptions)
		
	def partSize1(self, total):
		self.totalpartitions = int(total[1])
		if self.totalpartitions > 1:
			self.session.openWithCallback(self.partSize2,InputBox, title=_("Enter the size in Megabytes of the first partition:"), windowTitle = _("Partition size"), text="1", useableChars = "1234567890" )
		else:
			self.writePartFile()
			
	def partSize2(self, psize):
		if psize is None:
			psize = "100"
		self.p1size = psize
		if self.totalpartitions > 2:
			self.session.openWithCallback(self.partSize3,InputBox, title=_("Enter the size in Megabytes of the second partition:"), windowTitle = _("Partition size"), text="1", useableChars = "1234567890" )
		else:
			self.writePartFile()
			
	def partSize3(self, psize):
		if psize is None:
			psize = "100"
		self.p2size = psize
		if self.totalpartitions > 3:
			self.session.openWithCallback(self.partSize4,InputBox, title=_("Enter the size in Megabytes of the third partition:"), windowTitle = _("Partition size"), text="1", useableChars = "1234567890" )
		else:
			self.writePartFile()
		
	def partSize4(self, psize):
		if psize is None:
			psize = "100"
		self.p3size = psize
		self.writePartFile()
		
	def writePartFile(self):
		p1 = p2 = p3 = p4 = "0"
		device = "/dev/" + self.device
		out0 = "#!/bin/sh\n\nsfdisk %s << EOF\n" % (device)
		
		msg = _("Total Megabytes Available: \t") + str(self.totalsize)
		msg += _("\nPartition scheme:\n")
		p1 = self.p1size
		out1 = ",%sM\n" % (self.p1size)
		if self.totalpartitions == 1:
			p1 = str(self.totalsize)
			out1 = ";\n"
		msg += "%s1 \t size:%s M\n" % (device, p1)
		if self.totalpartitions > 1:
			p2 = self.p2size
			out2 = ",%sM\n" % (self.p2size)
			if self.totalpartitions == 2:
				p2 = self.totalsize - int(self.p1size)
				out2 = ";\n"
			msg += "%s2 \t size:%s M\n" % (device, p2)
		if self.totalpartitions > 2:
			p3 = self.p3size
			out3 = ",%sM\n" % (self.p3size)
			if self.totalpartitions == 3:
				p3 = self.totalsize - (int(self.p1size) + int(self.p2size))
				out3 = ";\n"
			msg += "%s3 \t size:%s M\n" % (device, p3)
		if self.totalpartitions > 3:
			p4 = self.totalsize - (int(self.p1size) + int(self.p2size) + int(self.p3size))
			out4 = ";\n"
			msg += "%s4 \t size:%s M\n" % (device, p4)
		msg +=_("\nWarning: all the data will be lost.\nAre you sure you want to format this device?\n")
		
		
		out = open("/tmp/sfdisk.tmp",'w')
		out.write(out0)
		out.write(out1)
		if self.totalpartitions > 1:
			out.write(out2)
		if self.totalpartitions > 2:
			out.write(out3)
		if self.totalpartitions > 3:
			out.write(out4)
		out.write("EOF\n")
		out.close()
		system("chmod 0755 /tmp/sfdisk.tmp")
		self["lab1"].setText(msg)
		
		if int(self.p1size) + int(self.p2size) + int(self.p3size) + int(self.p4size) > self.totalsize:
			self.wizClose(_("Sorry, your partition(s) sizes are bigger than total device size."))
		else:
			self.step = 5

	def do_Part(self):
		self.do_umount()
		self.canclose = False
		self["key_red"].hide()
		
		device = "/dev/%s" % (self.device)
		cmd = "umount -l " + device + "1"
		system(cmd)
		cmd = "echo -e 'Partitioning: %s \n\n'" % (device)
		cmd2 = "/tmp/sfdisk.tmp"
		self.session.open(Console, title=_("Partitioning..."), cmdlist=[cmd, cmd2], finishedCallback = self.partDone)
		
	def partDone(self):
		msg = _("The device has been partitioned.\nPartitions will be now formatted.")
		self["lab1"].setText(msg)
		self.step = 6
		
	def choiceBoxFstype(self):
		menu = []
#		menu.append((_("ext2 - recommended for USB flash memory"), "ext2"))
#		menu.append((_("ext3 - recommended for harddrives"), "ext3"))
		menu.append((_("ext4 - Recommended"), "ext4"))
		menu.append((_("fat32 - Only use for Media Files"), "vfat"))
		self.session.openWithCallback(self.choiceBoxFstypeCB, ChoiceBox, title=_("Choice filesystem."), list=menu)

	def choiceBoxFstypeCB(self, choice):
		if choice is None:
			return
		else:
			newfstype = choice[1]
			if newfstype == "ext4":
				self.formatcmd = "/sbin/mkfs.ext4 -F -O extent,flex_bg,large_file,uninit_bg -m1"
			elif newfstype == "ext3":
				self.formatcmd = "/sbin/mkfs.ext3 -F -m0"
			elif newfstype == "ext2":
				self.formatcmd = "/sbin/mkfs.ext2 -F -m0"
			elif newfstype == "vfat":
				self.formatcmd = "/usr/sbin/mkfs.vfat"
				
			self.do_Format()
		
	def do_Format(self):
		self.do_umount()
		os_remove("/tmp/sfdisk.tmp")
		cmds = ["sleep 1"]
		device = "/dev/%s1" % (self.device)
		cmd = "%s %s" % (self.formatcmd, device)
		cmds.append(cmd)
		if self.totalpartitions > 1:
			device = "/dev/%s2" % (self.device)
			cmd = "%s %s" % (self.formatcmd, device)
			cmds.append(cmd)
		if self.totalpartitions > 2:
			device = "/dev/%s3" % (self.device)
			cmd = "%s %s" % (self.formatcmd, device)
			cmds.append(cmd)
		if self.totalpartitions > 3:
			device = "/dev/%s4" % (self.device)
			cmd = "%s %s" % (self.formatcmd, device)
			cmds.append(cmd)
		
		self.session.open(Console, title=_("Formatting..."), cmdlist=cmds, finishedCallback = self.succesS)
	
	def step_Bump(self):
		if self.step == 1:
			self.stepOne()
		elif self.step == 2:
			self.stepTwo()
		elif self.step == 3:
			self.stepThree()
		elif self.step == 4:
			self.stepFour()
		elif self.step == 5:
			self.do_Part()
		elif self.step == 6:
			self.choiceBoxFstype()
			
	def get_Devicelist(self):
		devices = []
		folder = listdir("/sys/block")
		for f in folder:
			if f.find('sd') != -1:
				devices.append(f)
		return devices
			
	def get_Deviceinfo(self, device):
		info = vendor = model = size = ""
		filename = "/sys/block/%s/device/vendor" % (device)
		if fileExists(filename):
			vendor = file(filename).read().strip()
			filename = "/sys/block/%s/device/model" % (device)
			model = file(filename).read().strip()
			filename = "/sys/block/%s/size" % (device)
			size = int(file(filename).read().strip())
			cap = size / 1000 * 512 / 1024
			size = "%d.%03d GB" % (cap/1000, cap%1000)
			self.totalsize = cap
		info = _("Model: ") + vendor + " " + model +  "\n" + _("Size: ") + size + "\n" + _("Device: ") + "/dev/" + device
		return info
	
	def do_umount(self):
		f = open("/proc/mounts",'r')
		for line in f.readlines():
			if line.find("/dev/sd") != -1:					
				parts = line.split()
				cmd = "umount -l " + parts[0]
				system(cmd)
		f.close()
	
	def checkClose(self):
		if self.canclose == True:
			self.close()
			
	def wizClose(self, msg):
		self.session.openWithCallback(self.close, MessageBox, msg, MessageBox.TYPE_INFO)

	def succesS(self):
		mybox = self.session.openWithCallback(self.hreBoot, MessageBox, _("The Box will be now restarted to generate a new device UID.\nDon't forget to remap your device after the reboot.\nPress ok to continue"), MessageBox.TYPE_INFO)	
			
	def hreBoot(self, answer):
		self.session.open(TryQuitMainloop, 2)




