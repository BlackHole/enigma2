from os import path, mkdir, listdir, rename

from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigYesNo
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from .IPKInstaller import IpkgInstaller
from Screens.Console import Console
from Screens.Setup import Setup
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

config.scriptrunner = ConfigSubsection()
config.scriptrunner.close = ConfigYesNo(default=False)
config.scriptrunner.showinextensions = ConfigYesNo(default=False)


def updateExtensions(configElement):
	plugins.clearPluginList()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


config.scriptrunner.showinextensions.addNotifier(updateExtensions, initial_call=False)


def ScriptRunnerAutostart(reason, session=None, **kwargs):
	"""called with reason=1 during /sbin/shutdown.sysvinit, with reason=0 at startup"""
	pass


class OpenBhScriptRunner(IpkgInstaller):
	def __init__(self, session, list=None):
		if not list:
			list = []
			if path.exists("/usr/scripts") and not path.exists("/usr/script"):
				rename("/usr/scripts", "/usr/script")
			if not path.exists("/usr/script"):
				mkdir("/usr/script", 0o755)
			f = listdir("/usr/script")
			for line in f:
				parts = line.split()
				pkg = parts[0]
				if pkg.find(".sh") >= 0:
					list.append(pkg)
		IpkgInstaller.__init__(self, session, list)
		self.setTitle(_("Script runner"))

		self.skinName = ["OpenBhScriptRunner", "IpkgInstaller"]
		self["key_green"] = StaticText(_("Run"))
		self["key_menu"] = StaticText(_("MENU"))  # hook for automatic menu key

		self["myactions"] = ActionMap(
			["MenuActions"],
			{
				"menu": self.createSetup,
			}, -1)

	def createSetup(self):
		self.session.open(Setup, "openbhscriptrunner", "SystemPlugins/OBH")

	def install(self):
		list = self.list.getSelectionsList()
		cmdList = []
		for item in list:
			cmdList.append("chmod +x /usr/script/" + item[0] + " && . " + "/usr/script/" + str(item[0]))
		if len(cmdList) < 1 and len(self.list.list):
			cmdList.append("chmod +x /usr/script/" + self.list.getCurrent()[0][0] + " && . " + "/usr/script/" + str(self.list.getCurrent()[0][0]))
		if len(cmdList) > 0:
			self.session.open(Console, cmdlist=cmdList, closeOnSuccess=config.scriptrunner.close.value)
