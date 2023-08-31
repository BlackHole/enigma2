from os import listdir, path, stat

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigBoolean, configfile
from Components.SystemInfo import SystemInfo

from .BackupManager import BackupManagerautostart
from .ImageManager import ImageManagerautostart
from .IPKInstaller import IpkgInstaller
from .ScriptRunner import ScriptRunnerAutostart
from .SwapManager import SwapAutostart
from .IPKInstaller import IpkgInstaller


#	On plugin initialisation (called by StartEnigma). language will be assigned as follows if config.misc.firstrun.value:
#	Default language en_GB (OpenBh) is set by SetupDevices called by StartEnigma
#	If no backup, the languagewizard will be inserted by Plugin into the wizards.
#	If backup, then language will be set here from config.osd.language if in backup, else default language
#

def setLanguageFromBackup(backupfile):
	print("[OBH plugin][setLanguageFromBackup] backupfile", backupfile)
	import tarfile

	try:
		tar = tarfile.open(backupfile)
		member = tar.getmember("etc/enigma2/settings")
	except KeyError:
		print("[OBH plugin][setLanguageFromBackup] language selected failed")
		tar.close()
		return

	for line in tar.extractfile(member):
		line = line.decode()
		if line.startswith("config.osd.language"):
			languageToSelect = line.strip().split("=")[1]
			print("[OBH plugin][setLanguageFromBackup] language selected", languageToSelect)
			from Components.Language import language
			language.InitLang()
			language.activateLanguage(languageToSelect)
			config.misc.languageselected.value = 0		# 0 means found
			config.misc.languageselected.save()
			break
	tar.close()


def checkConfigBackup():
	backups = []
	for dir in ["/media/%s/backup" % media for media in listdir("/media/") if path.isdir(path.join("/media/", media))]:
		try:
			backups += [{"name": f, "mtime": stat(f).st_mtime} for x in listdir(dir) if (f := path.join(dir, x)) and path.isfile(f) and f.endswith(".tar.gz") and "vix" in f.lower()]
		except FileNotFoundError:  # e.g. /media/autofs/xxx will crash listdir if "xxx" is inactive
			pass
	if backups:
		backupfile = next(iter(sorted(backups, key=lambda x: x["mtime"], reverse=True)))["name"]  # select the most recent
		print("[RestoreWizard] Backup Image:", backupfile)
		return backupfile
	return None


if config.misc.firstrun.value and not config.misc.restorewizardrun.value:
	backupAvailable = checkConfigBackup()
	if backupAvailable:
		setLanguageFromBackup(backupAvailable)


def BHMenu(session):
	from .import ui
	return ui.BHMenu(session)


def UpgradeMain(session, **kwargs):
	session.open(BHMenu)


def startSetup(menuid):
	if menuid != "setup":
		return []
	return [(_("BH"), UpgradeMain, "bh_menu", 1010)]


def RestoreWizard(*args, **kwargs):
	from .RestoreWizard import RestoreWizard
	return RestoreWizard(*args, **kwargs)


def LanguageWizard(*args, **kwargs):
	from Screens.LanguageSelection import LanguageWizard
	return LanguageWizard(*args, **kwargs)

def BackupManager(session):
	from .BackupManager import OpenBhBackupManager
	return OpenBhBackupManager(session)


def BackupManagerMenu(session, **kwargs):
	session.open(BackupManager)


def ImageManager(session):
	from .ImageManager import OpenBhImageManager
	return OpenBhImageManager(session)


def ImageManagerMenu(session, **kwargs):
	session.open(ImageManager)


def ImageManagerStart(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Image Manager"), ImageManagerMenu, "image_manager", -1)]
	return []


def H9SDmanager(session):
	from .H9SDmanager import H9SDmanager
	return H9SDmanager(session)


def H9SDmanagerMenu(session, **kwargs):
	session.open(H9SDmanager)


def MountManager(session):
	from .MountManager import OpenBhDevicesPanel
	return OpenBhDevicesPanel(session)


def MountManagerMenu(session, **kwargs):
	session.open(MountManager)


def ScriptRunner(session):
	from .ScriptRunner import OpenBhScriptRunner
	return OpenBhScriptRunner(session)


def ScriptRunnerMenu(session, **kwargs):
	session.open(ScriptRunner)


def SwapManager(session):
	from .SwapManager import OpenBhSwap
	return OpenBhSwap(session)


def SwapManagerMenu(session, **kwargs):
	session.open(SwapManager)


def filescan_open(list, session, **kwargs):
	filelist = [x.path for x in list]
	session.open(IpkgInstaller, filelist)  # list


def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return Scanner(mimetypes=["application/x-debian-package"],
				paths_to_scan=[
					ScanPath(path="ipk", with_subdirs=True),
					ScanPath(path="", with_subdirs=False),
				],
				name="Ipkg",
				description=_("Install extensions."),
				openfnc=filescan_open)


def Plugins(**kwargs):
	if SystemInfo["MultiBootSlot"] == 0:  # only in recovery image
		plist = [PluginDescriptor(name=_("Image Manager"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=ImageManagerStart)]
		if not config.misc.firstrun.value:
			plist.append(PluginDescriptor(name=_("Vu+ ImageManager wizard"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=False, fnc=(30, ImageManager)))
		return plist

	plist = [PluginDescriptor(needsRestart=False, fnc=startSetup)]
	if config.scriptrunner.showinextensions.value:
		plist.append(PluginDescriptor(name=_("Script runner"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=ScriptRunnerMenu))
	plist.append(PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=SwapAutostart))
	plist.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=ImageManagerautostart))
	plist.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=BackupManagerautostart))
	plist.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=ScriptRunnerAutostart))
	if config.misc.firstrun.value and not config.misc.restorewizardrun.value:
		if backupAvailable:  # skip language wizard as it was set from the backup
			plist.append(PluginDescriptor(name=_("Restore wizard"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=False, fnc=(4, RestoreWizard)))
		else:
			plist.append(PluginDescriptor(name=_("Language Wizard"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=False, fnc=(1, LanguageWizard)))
	plist.append(PluginDescriptor(name=_("Ipkg"), where=PluginDescriptor.WHERE_FILESCAN, needsRestart=False, fnc=filescan))
	return plist
