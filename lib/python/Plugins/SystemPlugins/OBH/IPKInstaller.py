from os import listdir, path

from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config
from Components.Ipkg import IpkgComponent
from Components.Label import Label
from Components.MenuList import MenuList
from Components.SelectionList import SelectionList
from Components.Sources.StaticText import StaticText
from Screens.Console import Console
from Screens.Ipkg import Ipkg
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop


class OpenBhIPKInstaller(Screen):
	skin = ["""
	<screen name="OpenBhIPKInstaller" position="center,center" size="%d,%d">
		<ePixmap pixmap="skin_default/buttons/red.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
		<widget name="key_red" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
		<widget name="key_green" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="key_yellow" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
		<widget name="lab1" position="%d,%d" size="%d,%d" font="Regular; %d" zPosition="2" transparent="0" halign="center"/>
		<widget name="list" position="%d,%d" size="%d,%d" font="Regular;%d" scrollbarMode="showOnDemand"/>
		<applet type="onLayoutFinish">
			self["list"].instance.setItemHeight(%d)
		</applet>
	</screen>""",
		560, 400,  # screen
		0, 0, 140, 40,  # colors
		140, 0, 140, 40,
		280, 0, 140, 40,
		0, 0, 140, 40, 20,
		140, 0, 140, 40, 20,
		280, 0, 140, 40, 20,
		0, 50, 560, 50, 18,  # lab1
		10, 105, 540, 260, 20,  # list
		26,
			]  # noqa: E124

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("IPK installer"))

		self["lab1"] = Label()
		self.defaultDir = "/tmp"
		self.onChangedEntry = []
		self["myactions"] = ActionMap(
			["ColorActions", "OkCancelActions", "DirectionActions", "MenuActions"],
			{
				"cancel": self.close,
				"red": self.close,
				"green": self.keyInstall,
				"yellow": self.changelocation,
				"ok": self.keyInstall,
				"menu": self.close,
			}, -1)

		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button(_("Install"))
		self["key_yellow"] = Button()

		self.list = []
		self["list"] = MenuList(self.list)
		self.populate_List()

		if self.selectionChanged not in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary

		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		if item:
			name = item
			desc = ""
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def changelocation(self):
		if self.defaultDir == "/tmp":
			self["key_yellow"].setText(_("Extra IPK's"))
			self.defaultDir = config.backupmanager.xtraplugindir.value
			if not self.defaultDir:
				message = _("It seems you have not setup an extra location. Please set it up in the Backup manager setup menu.")
				ybox = self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
				ybox.setTitle(_("Change location"))
			elif self.defaultDir and not path.exists(self.defaultDir):
				message = _("Sorry but that location does not exist or is not setup. Please set it up in the Backup manager setup menu.")
				ybox = self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
				ybox.setTitle(_("Change location"))
			else:
				self.populate_List()
		else:
			self["key_yellow"].setText(_("Temp folder"))
			self.defaultDir = "/tmp"
			self.populate_List()

	def populate_List(self):
		if self.defaultDir == "/tmp":
			self["key_yellow"].setText(_("Extra IPK's"))
		else:
			self["key_yellow"].setText(_("Temp folder"))

		self["lab1"].setText(_("Select a package to install:"))

		del self.list[:]
		f = listdir(self.defaultDir)
		for line in f:
			if line.find(".ipk") != -1:
				self.list.append(line)

		if path.ismount("/media/usb"):
			f = listdir("/media/usb")
			for line in f:
				if line.find(".ipk") != -1:
					self.list.append(line)

		self.list.sort()
		self["list"].l.setList(self.list)

	def keyInstall(self):
		message = _("Are you ready to install ?")
		ybox = self.session.openWithCallback(self.Install, MessageBox, message, MessageBox.TYPE_YESNO)
		ybox.setTitle(_("Install confirmation"))

	def Install(self, answer):
		if answer is True:
			sel = self["list"].getCurrent()
			if sel:
				self.defaultDir = self.defaultDir.replace(" ", "%20")
				cmd1 = "/usr/bin/opkg install " + path.join(self.defaultDir, sel)
				self.session.openWithCallback(self.installFinished(sel), Console, title=_("Installing..."), cmdlist=[cmd1], closeOnSuccess=True)

	def installFinished(self, sel):
		message = _("Do you want to restart GUI now ?")
		ybox = self.session.openWithCallback(self.restBox, MessageBox, message, MessageBox.TYPE_YESNO)
		ybox.setTitle(_("Restart GUI."))

	def restBox(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.populate_List()
			self.close()

	def myclose(self):
		self.close()


class IpkgInstaller(Screen):
	skin = ["""
		<screen name="IpkgInstaller" position="center,center" size="%d,%d">
			<ePixmap pixmap="skin_default/buttons/red.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
			<ePixmap pixmap="skin_default/buttons/green.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
			<ePixmap pixmap="skin_default/buttons/blue.png" position="%d,%d" size="%d,%d" alphatest="blend" scale="1"/>
			<widget source="key_red" render="Label" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
			<widget source="key_green" render="Label" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
			<widget source="key_yellow" render="Label" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
			<widget source="key_blue" render="Label" position="%d,%d" zPosition="1" size="%d,%d" font="Regular;%d" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>
			<widget name="list" position="%d,%d" size="%d,%d" font="Regular;%d"/>
			<ePixmap pixmap="skin_default/div-h.png" position="%d,%d" zPosition="10" size="%d,%d" transparent="1" alphatest="blend" scale="1"/>
			<widget source="introduction" render="Label" position="%d,%d" zPosition="10" size="%d,%d" halign="center" valign="center" font="Regular;%d" transparent="1" shadowColor="black" shadowOffset="-1,-1"/>
		</screen>""",
			560, 450,  # screen
			0, 0, 140, 40,  # colors
			140, 0, 140, 40,
			280, 0, 140, 40,
			420, 0, 140, 40,
			0, 0, 140, 40, 20,
			140, 0, 140, 40, 20,
			280, 0, 140, 40, 20,
			420, 0, 140, 40, 20,
			5, 50, 540, 360, 20,  # list
			0, 410, 560, 2,
			5, 420, 550, 30, 22,
			]  # noqa: E124

	def __init__(self, session, list):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("IPK installer"))
		self.list = SelectionList()
		self["list"] = self.list
		for listindex in range(len(list)):
			if not list[listindex].split("/")[-1].startswith("._"):
				self.list.addSelection(list[listindex].split("/")[-1], list[listindex], listindex, False)

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))

		self["actions"] = ActionMap(
			["OkCancelActions", "ColorActions"],
			{
				"ok": self.list.toggleSelection,
				"cancel": self.close,
				"red": self.close,
				"green": self.install,
				"blue": self.list.toggleAllSelection
			}, -1)

	def install(self):
		list = self.list.getSelectionsList()
		cmdList = []
		for item in list:
			cmdList.append((IpkgComponent.CMD_INSTALL, {"package": item[1]}))
		self.session.open(Ipkg, cmdList=cmdList)
