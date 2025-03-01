from Screens.Screen import Screen
from Screens.Setup import Setup
from Components.config import getConfigListEntry, NoSave, ConfigPassword, ConfigText
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.Button import Button
from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap, HelpableNumberActionMap
import os
from urllib.parse import urlsplit, quote, unquote

class openbhVipMain(Setup): # ConfigListScreen):
	def __init__(self, session):
		username = None
		password = None
		if os.path.exists("/etc/opkg/vip-feed.conf"):
			with open("/etc/opkg/vip-feed.conf", "r") as f:
				for line in f.readlines():
					token = line.split()
					if len(token) == 3:
						username = unquote(urlsplit(token[2]).username)
						password = unquote(urlsplit(token[2]).password)

		if username == None:
			username = ""
		if password == None:
			password = ""

		self.username = ConfigText(default=username, fixed_size=False)
		self.password = NoSave(ConfigPassword(default=password))

		self.setup_title = _("OpenBh VIP Feed Setup")
		Setup.__init__(self, session=session, setup=None)
		self.skinName = "Setup"
		self.createSetup()
		self["key_green"] = StaticText(_("Save"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_yellow"] = StaticText("Virtual Keyboard")
		self["key_blue"] = StaticText("")
		self["key_exit"] = StaticText("Cancel")
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"cancel": (self.close, _("Exit")),
		})
		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
		        "red": (self.close, _("Exit")),
		        "green": (self.okbuttonClick, _("Save Feed")),
		        "yellow": (self.okbuttonClick, _("Virtual Keyboard")),
		})
		self["InputBoxActions"] = HelpableNumberActionMap(self, ["WizardActions", "InputBoxActions", "InputAsciiActions", "KeyboardInputActions", "ColorActions", "VirtualKeyboardActions", "OkCancelActions"],
		{
				"yellow": (self.keyText, _("Virtual Keyboard")),
				"ok": (self.keyText, _("OK")),
		}, prio=-1)

		self.onLayoutFinish.append(self.__layoutFinished)

	def okbuttonClick(self):
		with open("/etc/opkg/vip-feed.conf", "w") as f:
			f.write(f"src/gz openbh-vip https://{quote(self.username.value)}:{quote(self.password.value)}@feeds.openbh.net/vip\n")
		self.close()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_('Forum Username'), self.username, _("Please enter your forum username to configure the VIP feed")))
		self.list.append(getConfigListEntry(_('Forum Password'), self.password, _("Please enter your forum password to configure the VIP feed")))
		self['config'].list = self.list

	def __layoutFinished(self):
		self.setTitle(self.setup_title)

def main(session, **kwargs):
	session.open(openbhVipMain)

def Plugins(**kwargs):
	return PluginDescriptor(name="OpenBh VIP", description="Configure the OpenBh VIP feed", icon="openbh.png", where=PluginDescriptor.WHERE_PLUGINMENU, needsRestart=False, fnc=main)

