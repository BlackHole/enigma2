from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.ActionMap import ActionMap
from Components.config import config, ConfigText, configfile
from Components.Sources.List import List
from Components.Label import Label
from Components.PluginComponent import plugins
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_SKIN_IMAGE, fileExists, pathExists, createDir
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from os import system, listdir, chdir, getcwd, remove as os_remove
from enigma import eDVBDB

config.misc.fast_plugin_button = ConfigText(default="")

class DeliteGreenPanel(Screen):
	skin = """
	<screen name="DeliteGreenPanel" position="center,center" size="1000,720" title="Black Hole Green Panel" flags="wfNoBorder">
		<eLabel text="Black Hole Green Panel" position="80,30" size="800,38" font="Regular;34" halign="left" foregroundColor="#004c74" backgroundColor="transpBlack" transparent="1"/>
		<widget source="list" render="Listbox" position="80,105" zPosition="1" size="840,500" scrollbarMode="showOnDemand"  transparent="1">
			<convert type="TemplatedMultiContent">
				{"template": [
				MultiContentEntryText(pos = (125, 0), size = (650, 24), font=0, text = 0),
				MultiContentEntryText(pos = (125, 24), size = (650, 24), font=1, text = 1),
				MultiContentEntryPixmapAlphaTest(pos = (6, 5), size = (100, 40), png = 2),
				],
				"fonts": [gFont("Regular", 24),gFont("Regular", 20)],
				"itemHeight": 50
				}
			</convert>
		</widget>
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

		self["key_red"] = Label(_("Fast Plug. Setup"))
		self["key_green"] = Label(_("Fast Plug"))
		self["key_yellow"] = Label(_("Addons"))
		self["key_blue"] = Label(_("Scripts"))

		self.list = []
		self["list"] = List(self.list)
		self.updateList()

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.runPlug,
			"back": self.close,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue
		}, -1)

	def runPlug(self):
		mysel = self["list"].getCurrent()
		if mysel:
			plugin = mysel[3]
			plugin(session=self.session)

	def updateList(self):
		self.list = [ ]
		self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		for plugin in self.pluginlist:
			if plugin.icon is None:
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/plugin.png"))
			else:
				png = plugin.icon
			res = (plugin.name, plugin.description, png, plugin)
			self.list.append(res)

		self["list"].list = self.list

	def keyYellow(self):
		from Screens.BpAd import DeliteAddons
		self.session.open(DeliteAddons)

	def keyRed(self):
		self.session.open(DeliteSetupFp)

	def keyGreen(self):
		runplug = None
		for plugin in self.list:
			if  plugin[3].name == config.misc.fast_plugin_button.value:
				runplug = plugin[3]
				break

		if runplug is not None:
			runplug(session=self.session)
		else:
			self.session.open(MessageBox, _("Fast Plugin not found. You have to setup Fast Plugin before to use this shortcut."), MessageBox.TYPE_INFO)

	def keyBlue(self):
		self.session.open(DeliteScript)

class DeliteSetupFp(Screen):
	skin = """
	<screen position="160,115" size="390,370" title="Black Hole Fast Plugin Setup">
		<widget source="list" render="Listbox" position="10,10" size="370,300" scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
		<ePixmap pixmap="skin_default/buttons/red.png" position="115,320" size="140,40" alphatest="on" />
		<widget name="key_red" position="115,320" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Label(_("Set Favourite"))
		self.list = []
		self["list"] = List(self.list)
		self.updateList()

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.save,
			"back": self.close,
			"red": self.save
		}, -1)

	def updateList(self):
		self.list = [ ]
		self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		for plugin in self.pluginlist:
			if plugin.icon is None:
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/plugin.png"))
			else:
				png = plugin.icon
			res = (plugin.name, plugin.description, png)
			self.list.append(res)

		self["list"].list = self.list

	def save(self):
		mysel = self["list"].getCurrent()
		if mysel:
			message = _("Fast plugin set to: ") + mysel[0] + _("\nKey: 2x Green")
			mybox = self.session.openWithCallback(self.close, MessageBox, message, MessageBox.TYPE_INFO)
			mybox.setTitle(_("Configuration Saved"))
			config.misc.fast_plugin_button.value = mysel[0]
			config.misc.fast_plugin_button.save()
			configfile.save()

class DeliteScript(Screen):
	skin = """
	<screen position="80,100" size="560,410" title="Black Hole Script Panel">
		<widget source="list" render="Listbox" position="10,10" size="540,300" scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
		<widget name="statuslab" position="10,320" size="540,30" font="Regular;16" valign="center" noWrap="1" backgroundColor="#333f3f3f" foregroundColor="#FFC000" shadowOffset="-2,-2" shadowColor="black" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="210,360" size="140,40" alphatest="on" />
		<widget name="key_green" position="210,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["statuslab"] = Label("N/A")
		self["key_green"] = Label(_("Execute"))
		self.mlist = []
		self.populateSL()
		self["list"] = List(self.mlist)
		self["list"].onSelectionChanged.append(self.schanged)

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.myGo,
			"back": self.close,
			"green": self.myGo
		})
		self.onLayoutFinish.append(self.refr_sel)

	def refr_sel(self):
		self["list"].index = 1
		self["list"].index = 0

	def populateSL(self):
		myscripts = listdir("/usr/script")
		for fil in myscripts:
			if fil.find('.sh') != -1:
				fil2 = fil[:-3]
				desc = "N/A"
				f = open("/usr/script/" + fil,'r')
				for line in f.readlines():
					if line.find('#DESCRIPTION=') != -1:
						line = line.strip()
						desc = line[13:]
				f.close()
				res = (fil2, desc)
				self.mlist.append(res)

	def schanged(self):
		mysel = self["list"].getCurrent()
		if mysel:
			mytext = " " + mysel[1]
			self["statuslab"].setText(mytext)

	def myGo(self):
		mysel = self["list"].getCurrent()
		if mysel:
			mysel = mysel[0]
			mysel2 = "/usr/script/" + mysel + ".sh"
			mytitle = _("Black Hole E2 Script: ") + mysel
			self.session.open(Console, title=mytitle, cmdlist=[mysel2])