from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from boxbranding import getMachineBrand, getImageBuild, getMachineName, getImageVersion, getImageType
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.Pixmap import MultiPixmap
from Components.About import about
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigText, getConfigListEntry, ConfigSelection, NoSave
from Tools.Directories import fileExists
from ServiceReference import ServiceReference
from os import system, listdir, path, remove as os_remove, rename as os_rename
from enigma import iServiceInformation, eTimer
import socket


class DeliteBluePanel(Screen):
	skin = """
	<screen name="DeliteBluePanel" position="center,center" size="1000,720"  title="OpenBh Blue Panel" flags="wfNoBorder">
		<ePixmap position="339,170" zPosition="3" size="60,40" pixmap="skin_default/buttons/key_ok.png" alphatest="blend" transparent="1" />
		<eLabel text="OpenBh Blue Panel" position="80,30" size="800,38" font="Regular;34" halign="left" transparent="1"/>
		<widget name="lab1" position="129,90" size="230,25" font="Regular;24" zPosition="2"  transparent="1"/>
		<widget name="list" position="75,126" size="340,38" zPosition="2"  transparent="1"/>
		<widget name="lab2" position="139,172" size="190,24" font="Regular;20" halign="center" valign="center" zPosition="2" transparent="1"/>
		<widget name="lab3" position="79,201" size="120,28" font="Regular;24" halign="left" zPosition="2" transparent="1"/>
		<widget name="activecam" position="79,201" size="350,28" font="Regular;24" halign="left" zPosition="2" transparent="1"/>
		<widget name="Ilab1" position="79,257" size="350,28" font="Regular;24" zPosition="2" transparent="1"/>
		<widget name="Ilab2" position="79,290" size="350,28" font="Regular;24" zPosition="2" transparent="1"/>
		<widget name="Ilab3" position="79,315" size="350,28" font="Regular;24" zPosition="2" transparent="1"/>
		<widget name="Ilab4" position="79,345" size="350,28" font="Regular;24" zPosition="2" transparent="1"/>
		<widget name="Ecmtext" position="79,380" size="440,300" font="Regular;20" zPosition="2" transparent="1"/>
		<ePixmap position="88,650" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" zPosition="1" />
		<ePixmap position="316,650" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" zPosition="1" />
		<ePixmap position="544,650" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="on" zPosition="1" />
		<ePixmap position="772,650" size="140,40" pixmap="skin_default/buttons/blue.png" alphatest="on" zPosition="1" />
		<widget name="key_red" position="88,650" zPosition="2" size="140,40" font="Regular;24" halign="center" valign="center" backgroundColor="red" transparent="1" />
		<widget name="key_green" position="316,650" zPosition="2" size="140,40" font="Regular;24" halign="center" valign="center" backgroundColor="green" transparent="1" />
		<widget name="key_yellow" position="544,650" zPosition="2" size="140,40" font="Regular;24" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
		<widget name="key_blue" position="772,650" zPosition="2" size="140,40" font="Regular;24" halign="center" valign="center" backgroundColor="blue" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["lab1"] = Label()
		self["lab2"] = Label(_("Set Default CAM"))
		self["lab3"] = Label()
		self["Ilab1"] = Label()
		self["Ilab2"] = Label()
		self["Ilab3"] = Label()
		self["Ilab4"] = Label()
		self["key_red"] = Label(_("Autocam"))
		self["key_green"] = Label(_("Cam Info"))
		self["key_yellow"] = Label(_("System Info"))
		self["key_blue"] = Label(_("Extra Settings"))
		self["activecam"] = Label()
		self["Ecmtext"] = ScrollLabel()

		self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"],
		{
			"ok": self.keyOk,
			"cancel": self.close,
			"green": self.keyGreen,
			"red": self.keyRed,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"up": self["Ecmtext"].pageUp,
			"down": self["Ecmtext"].pageDown
		}, -1)

		self.emlist = []
		self["list"] = MenuList(self.emlist)
		self.onShow.append(self.updateBP0)

	def updateBP0(self):
		self.emlist = []
		self.check_scriptexists()
		self.check_camexists()
		self.populate_List()
		self["list"].setList(self.emlist)
		self["lab1"].setText(_("%d  CAMs Installed") % (len(self.emlist)))
		self.updateBP()

	def check_camexists(self):
		if not path.exists("/usr/softcams"):
			return
		if path.exists("/usr/camscript"):
			cams = listdir("/usr/camscript/")
			for fil in cams:
				self.ch_ca2(fil)

	def ch_ca2(self, script):
		if script == "Ncam_Ci.sh":
			return
		name = script.replace('Ncam_', '').replace('.sh', '')
		cams = listdir("/usr/softcams/")
		for fil in cams:
			if fil == name:
				return
		vc = False
		filein = "/usr/camscript/" + script
		f = open(filein,'r')
		for line in f.readlines():
			if line.find('/usr/softcams/') != -1:
				vc = True
				break
		f.close()
		if vc == True:
			os_remove(filein)

	def check_scriptexists(self):
		if path.exists("/usr/softcams"):
			cams = listdir("/usr/softcams")
			for fil in cams:
				self.ch_sc2(fil)

	def ch_sc2(self, name):
		scriptname = "Ncam_" + name +".sh"
		cams = listdir("/usr/camscript/")
		for fil in cams:
			if fil == scriptname:
				return
		fileout = "/usr/camscript/" + scriptname
		out = open(fileout, "w")
		f = open("/usr/camscript/Ncam_Ci.sh",'r')
		for line in f.readlines():
			if line.find('CAMNAME=') != -1:
				line = "CAMNAME=\"" + name + "\""
			if line.find('daemon -S') != -1:
				line = "\t/usr/softcams/" + name +"\n"
				if name.find('oscam') != -1 or name.find('ncam') != -1:
					line = line.rstrip() + " -b -c /etc/tuxbox/config/" + name +"\n"
			if line.find('daemon -K') != -1:
				line = "\t killall -9 " + name +" 2 >/dev/null\n\tsleep 2\n\tremove_tmp\n"
			out.write(line)
		system("chmod 0755 " + fileout)
		f.close()
		out.close()


	def populate_List(self):
		self.camnames = {}
		cams = listdir("/usr/camscript")
		for fil in cams:
			if fil.find('Ncam_') != -1:
				f = open("/usr/camscript/" + fil, 'r')
				for line in f.readlines():
					line = line.strip()
					if line.find('CAMNAME=') != -1:
						name = line[9:-1]
						self.emlist.append(name)
						self.camnames[name] = "/usr/camscript/" + fil
				f.close()

	def updateBP(self):
		try:
			name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
			sinfo = self.session.nav.getCurrentService().info()
			provider = self.getServiceInfoValue(iServiceInformation.sProvider, sinfo)
			wide = self.getServiceInfoValue(iServiceInformation.sAspect, sinfo)
			width = sinfo and sinfo.getInfo(iServiceInformation.sVideoWidth) or -1
			height = sinfo and sinfo.getInfo(iServiceInformation.sVideoHeight) or -1
			videosize = "%dx%d" % (width, height)
			aspect = "16:9"
			if aspect in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE):
				aspect = "4:3"
		except:
			name = "N/A"
			provider = "N/A"
			aspect = "N/A"
			videosize = "N/A"

		self["Ilab1"].setText(_("Name: ") + name)
		self["Ilab2"].setText(_("Provider: ") + provider)
		self["Ilab3"].setText(_("Aspect Ratio: ") + aspect)
		self["Ilab4"].setText(_("Videosize: ") + videosize)

		self.defaultcam = "/usr/camscript/Ncam_Ci.sh"
		check = False
		if fileExists("/etc/BhCamConf"):
			f = open("/etc/BhCamConf", 'r')
			for line in f.readlines():
				parts = line.strip().split("|")
				if parts[0] == "deldefault":
					self.defaultcam = parts[1]
				elif parts[0] == "delcurrent":
					check = True
			f.close()

		if check == False:
			out = open("/etc/BhCamConf",'w')
			line = "deldefault|" + self.defaultcam + "\n"
			out.write(line)
			line = "delcurrent|" + self.defaultcam + "\n"
			out.write(line)
			out.close()

		self.defCamname = "Common Interface"
		for c in list(self.camnames.keys()):
			if self.camnames[c] == self.defaultcam:
				self.defCamname = c
		pos = 0
		for x in self.emlist:
			if x == self.defCamname:
				self["list"].moveToIndex(pos)
				break
			pos += 1

		mytext = ""
		if fileExists("/tmp/ecm.info"):
			f = open("/tmp/ecm.info", 'r')
			for line in f.readlines():
				mytext = mytext + line.strip() + "\n"
			f.close()
		if len(mytext) < 5:
			mytext = "\n\n    " + _("Ecm Info not available.")

		self["activecam"].setText(self.defCamname)
		self["Ecmtext"].setText(mytext)

	def getServiceInfoValue(self, what, myserviceinfo):
		v = myserviceinfo.getInfo(what)
		if v == -2:
			v = myserviceinfo.getInfoString(what)
		elif v == -1:
			v = "N/A"
		return v

	def keyOk(self):
		self.sel = self["list"].getCurrent()
		self.newcam = self.camnames[self.sel]

		inme = open("/etc/BhCamConf",'r')
		out = open("/etc/BhCamConf.tmp",'w')
		for line in inme.readlines():
			if line.find("delcurrent") == 0:
				line = "delcurrent|" + self.newcam + "\n"
			elif line.find("deldefault") == 0:
				line = "deldefault|" + self.newcam + "\n"
			out.write(line)
		out.close()
		inme.close()
		os_rename("/etc/BhCamConf.tmp", "/etc/BhCamConf")

		out = open("/etc/CurrentBhCamName", "w")
		out.write(self.sel)
		out.close()
		cmd = "cp -f " + self.newcam + " /usr/bin/StartBhCam"
		system(cmd)
		cmd = "STOP_CAMD," + self.defaultcam
		self.sendtoBh_sock(cmd)
#		cmd = self.defaultcam + " stop"
#		system(cmd)

		cmd = "NEW_CAMD," + self.newcam
		self.sendtoBh_sock(cmd)
		oldcam = self.camnames[self.sel]
		self.session.openWithCallback(self.myclose, Nab_DoStartCam, self.sel)

	def sendtoBh_sock(self, data):
		client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		client_socket.connect("/tmp/Blackhole.socket")
		client_socket.send(data.encode('utf-8'))
		client_socket.close()

	def keyYellow(self):
		self.session.open(BhsysInfo)

	def keyBlue(self):
		from Screens.BpSet import DeliteSettings
		self.session.open(DeliteSettings)

	def keyGreen(self):
		cam = "0"
		if fileExists("/tmp/.ncam/ncam.version") or fileExists("/tmp/.oscam/oscam.version"):
			from Screens.OScamInfo import OscamInfoMenu
			self.session.open(OscamInfoMenu)
		elif fileExists("/tmp/.CCcam.nodeid"):
			from Screens.CCcamInfo import CCcamInfoMain
			self.session.open(CCcamInfoMain)
		else :
			self.session.open(MessageBox, _("Please use OScam, Ncam or CCcam to get info."), MessageBox.TYPE_INFO)



	def keyRed(self):
#		self.session.open(BhEpgPanel)
		self.session.open(DeliteAutocamMan2)

	def myclose(self):
		self.close()


class Nab_DoStartCam(Screen):
	skin = """
	<screen position="390,100" size="484,250" title="OpenBh" flags="wfNoBorder">
		<widget name="connect" position="0,0" size="484,250" zPosition="-1" pixmaps="skin_default/startcam_1.png,skin_default/startcam_2.png,skin_default/startcam_3.png,skin_default/startcam_4.png" transparent="1" />
		<widget name="lab1" position="10,180" halign="center" size="460,60" zPosition="1" font="Regular;20" valign="top" transparent="1" />
	</screen>"""

	def __init__(self, session, title):
		Screen.__init__(self, session)

		msg = _("Please wait while starting\n") + title + "..."
		self["connect"] = MultiPixmap()
		self["lab1"] = Label(msg)

		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updatepix)
		self.onShow.append(self.startShow)
		self.onClose.append(self.delTimer)

	def startShow(self):
		self.curpix = 0
		self.count = 0
		self["connect"].setPixmapNum(0)
		self.activityTimer.start(10)

	def updatepix(self):
		self.activityTimer.stop()
		if self.curpix > 2:
			self.curpix = 0
		#if self.count == 0:

		if self.count > 7:
			self.curpix = 3
		self["connect"].setPixmapNum(self.curpix)
		if self.count == 20:
			self.hide()

			#ref = self.session.nav.getCurrentlyPlayingServiceReference()
			#self.session.nav.playService(ref)
			self.close()

		self.activityTimer.start(140)
		self.curpix += 1
		self.count += 1

	def delTimer(self):
		del self.activityTimer


class BhsysInfo(Screen):
	skin = """
	<screen position="center,center" size="1020,600" title="OpenBh Info" flags="wfNoBorder">
		<widget name="lab1" position="50,25" halign="left" size="1020,550" zPosition="1" font="Regular;20" valign="top" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["lab1"] = ScrollLabel()

		self.onShow.append(self.updateInfo)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"up": self["lab1"].pageUp,
			"down": self["lab1"].pageDown
		}, -1)

	def updateInfo(self):
		rc = system("df -h > /tmp/syinfo.tmp")
		text =  _("STB \n") +_("Brand:") + "\t%s\n" % getMachineBrand()
		text += _("Model:\t%s \n") % (getMachineName())
		text += _("Chipset:\t%s \n") % about.getChipSetString().upper() + "\n"
		text += _("MEMORY\n")
		memTotal = memFree = swapTotal = swapFree = 0
		for line in open("/proc/meminfo", 'r'):
			parts = line.replace("k", "K").split(':')
			key = parts[0].strip()
			if key == "MemTotal":
				memTotal = parts[1].strip()
			elif key in ("MemFree", "Buffers", "Cached"):
				memFree += int(parts[1].strip().split(' ', 1)[0])
			elif key == "SwapTotal":
				swapTotal = parts[1].strip()
			elif key == "SwapFree":
				swapFree = parts[1].strip()
		text += _("Total memory:") + "\t%s\n" % memTotal
		text += _("Free memory:") + "\t%s KB\n" % memFree
		text += _("Swap total:") + "\t%s \n" % swapTotal
		text += _("Swap free:") + "\t%s \n" % swapFree
		text += "\n" + _("STORAGE") + "\n"
		f = open("/tmp/syinfo.tmp", 'r')
		line = f.readline()
		parts = line.split()
		text += _("Filesystem:") + "\t" + "{0:<16}".format(parts[1]) + "{0:<15}".format(parts[2]) + "{0:<14}".format(parts[3]) + "{0:<14}".format(parts[4]) + "\n"
		line = f.readline()
		parts = line.replace('M', 'MB').replace('G', 'GB').replace('K', 'KB').split()
		text += _("Flash:") + "\t" + "{0:<14}".format(parts[1]) + "{0:<12}".format(parts[2]) + "{0:<14}".format(parts[3]) + "{0:<0}".format(parts[4]) + "\n"
		for line in f.readlines():
			if line.find('/media/') != -1:
				line = line.replace('/media/', '').replace('hdd', 'Hdd:').replace('usb', 'Usb:')
				parts = line.split()
				if len(parts) == 6:
					if line.find('Hdd:') != -1:
						parts = line.replace('M', 'MB').replace('G', 'GB').replace('K', 'KB').split()
						text +=_("Hdd:") + "\t" + "{0:<12}".format(parts[1]) + "{0:<12}".format(parts[2]) + "{0:<13}".format(parts[3]) + "{0:<14}".format(parts[4]) + "\n"
				if len(parts) == 6:
					if line.find('Usb:') != -1:
						parts = line.replace('M', 'MB').replace('G', 'GB').replace('K', 'KB').split()
						text +=_("Usb:") + "\t" + "{0:<14}".format(parts[1]) + "{0:<14}".format(parts[2]) + "{0:<14}".format(parts[3]) + "{0:<14}".format(parts[4]) + "\n"
		f.close()
		os_remove("/tmp/syinfo.tmp")

		text += "\n" + _("SOFTWARE") + "\n"
		text += "Image:\t" + "OpenBh %s.%s (%s)\n" % (getImageVersion(), getImageBuild(), getImageType().title())
		text += "Enigma2: \t" + about.getEnigmaVersionString() + "\n"
		text += "Kernel: \t" + about.getKernelVersionString() + "\n"
		self["lab1"].setText(text)


class BhEpgPanel(Screen):
	skin = """
	<screen position="center,center" size="600,400" title="OpenBh EPG Panel">
		<widget source="list" render="Listbox" position="20,20" size="560,360" font="Regular;28" itemHeight="40"  scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		flist = [("EPGSettings"), ("CrossEPG"), ("EPGImport"), ("EPGSearch")]
		self["list"] = List(flist)

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.KeyOk,
			"back": self.close

		})

	def KeyOk(self):
		sel = self["list"].getCurrent()
		if sel:
			if sel == "CrossEPG":
				from Plugins.SystemPlugins.CrossEPG.crossepg_main import crossepg_main
				crossepg_main.setup(self.session)
			elif sel == "EPGSettings":
				from Screens.Setup import Setup
				self.session.open(Setup, "epgsettings")
			elif sel == "EPGImport":
				from Plugins.Extensions.EPGImport.plugin import main as xmltv
				xmltv(self.session)
			elif sel == "EPGSearch":
				#from Plugins.Extensions.EPGSearch.plugin import main as epgsearch
				#epgsearch(self.session)
				from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch as epgsearch
				self.session.open(epgsearch)

class DeliteAutocamMan2(Screen):
	skin = """
	<screen position="center,center" size="800,520" title="OpenBh Autocam Manager">
		<widget name="defaultcam" position="10,10" size="780,30" font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313" />
		<widget source="list" render="Listbox" position="20,60" size="760,400" scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
    		<ePixmap pixmap="skin_default/buttons/red.png" position="200,480" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="440,480" size="140,40" alphatest="on" />
		<widget name="key_red" position="200,480" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="440,480" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
    	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Add"))
		self["defaultcam"] = Label(_("Default Cam:"))
		self.emlist = []
		self.camnames = {}

		self.list = []
		self["list"] = List(self.list)

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.close,
			"back": self.close,
			"red": self.deltocam,
			"green": self.addtocam
		})

		self.updateList()

	def addtocam(self):
		self.session.openWithCallback(self.updateList, DeliteSetupAutocam2)

	def updateList(self):
		self.list = [ ]
		cams = listdir("/usr/camscript")
		for fil in cams:
			if fil.find('Ncam_') != -1:
				f = open("/usr/camscript/" + fil,'r')
				for line in f.readlines():
					if line.find('CAMNAME=') != -1:
						line = line.strip()
						cn = line[9:-1]
						self.emlist.append(cn)
						self.camnames[cn] = "/usr/camscript/" + fil


				f.close()

		if fileExists("/etc/BhCamConf"):
			f = open("/etc/BhCamConf",'r')
			for line in f.readlines():
				parts = line.strip().split("|")
				if parts[0] == "delcurrent":
					continue
				elif parts[0] == "deldefault":
					defaultcam = self.GetCamName(parts[1])
					self["defaultcam"].setText(_("Default Cam:  ") + defaultcam)
				else:
					text = parts[2] + "\t" + self.GetCamName(parts[1])
					res = (text, parts[0])
					self.list.append(res)

			f.close()
		self["list"].list = self.list

	def GetCamName(self, cam):
		activeCam = ""
		for c in self.camnames.keys():
			if self.camnames[c] == cam:
				activeCam = c
		return activeCam

	def deltocam(self):
		mysel = self["list"].getCurrent()
		if mysel:
			mysel = mysel[1]
			out = open("/etc/BhCamConf.tmp", "w")
			f = open("/etc/BhCamConf",'r')
			for line in f.readlines():
				parts = line.strip().split("|")
				if parts[0] != mysel:
					out.write(line)
			f.close()
			out.close()
			os_rename("/etc/BhCamConf.tmp", "/etc/BhCamConf")
			self.updateList()


class DeliteSetupAutocam2(Screen, ConfigListScreen):
	skin = """
	<screen position="center,center" size="800,340" title="OpenBh Autocam Setup">
		<widget name="config" position="10,20" size="780,280" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="330,270" size="140,40" alphatest="on" />
		<widget name="key_green" position="330,270" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self["key_green"] = Label(_("Save"))

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"green": self.saveMyconf,
			"back": self.close

		})
		self.updateList()

	def updateList(self):
		mychoices = []
		self.chname = "Unknown"
		self.chref = "Unknown"

		myservice = self.session.nav.getCurrentService()
		if myservice is not None:
			myserviceinfo = myservice.info()
			if self.session.nav.getCurrentlyPlayingServiceReference():
				self.chname = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
				self.chref = self.session.nav.getCurrentlyPlayingServiceReference().toString()
		cams = listdir("/usr/camscript")
		for fil in cams:
			if fil.find('Ncam_') != -1:
				f = open("/usr/camscript/" + fil,'r')
				for line in f.readlines():
					if line.find('CAMNAME=') != -1:
						line = line.strip()
						cn = line[9:-1]
						cn2 = "/usr/camscript/" + fil
						res = (cn2, cn)
						mychoices.append(res)
				f.close()

		self.autocam_file = NoSave(ConfigSelection(choices = mychoices))

		res = getConfigListEntry(self.chname, self.autocam_file)
		self.list.append(res)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def saveMyconf(self):
		check = True
		if fileExists("/etc/BhCamConf"):
			f = open("/etc/BhCamConf",'r')
			for line in f.readlines():
				parts = line.strip().split("|")
				if parts[0] == self.chref:
					check = False
			f.close()

		if check == True:
			line = self.chref + "|" + self.autocam_file.value + "|" + self.chname + "\n"
			out = open("/etc/BhCamConf", "a")
			out.write(line)
			out.close()
		self.close()



class DeliteBp:
	def __init__(self):
		self["DeliteBp"] = ActionMap(["InfobarExtensions"],
			{
				"DeliteBpshow": (self.showDeliteBp),
			})

	def showDeliteBp(self):
		self.session.openWithCallback(self.callNabAction, DeliteBluePanel)

	def callNabAction(self, *args):
		if len(args):
			(actionmap, context, action) = args
			actionmap.action(context, action)
