from boxbranding import getMachineMtdKernel, getMachineMtdRoot
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Screens.Screen import Screen
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop


STARTUP = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % getMachineMtdRoot()					# /STARTUP
STARTUP_RECOVERY = "kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % getMachineMtdRoot() 			# /STARTUP_RECOVERY
STARTUP_1 = "kernel=/linuxrootfs1/zImage root=/dev/%s rootsubdir=linuxrootfs1" % getMachineMtdRoot() 	# /STARTUP_1
STARTUP_2 = "kernel=/linuxrootfs2/zImage root=/dev/%s rootsubdir=linuxrootfs2" % getMachineMtdRoot() 	# /STARTUP_2
STARTUP_3 = "kernel=/linuxrootfs3/zImage root=/dev/%s rootsubdir=linuxrootfs3" % getMachineMtdRoot() 	# /STARTUP_3

class VuplusKexec(Screen):

	skin = """
	<screen name="VuplusKexec" position="center,center" size="750,700" flags="wfNoBorder" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="750,700" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="748,698" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="60,10" foregroundColor="#00ffffff" size="480,50" halign="left" font="Regular; 28" backgroundColor="#00000000" />
		<eLabel name="line" position="1,60" size="748,1" backgroundColor="#00ffffff" zPosition="1" />
		<eLabel name="line2" position="1,250" size="748,4" backgroundColor="#00ffffff" zPosition="1" />
		<widget source="labe14" render="Label" position="2,80" size="730,30" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_red" render="Label" position="30,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="200,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_yellow" render="Label" position="370,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="200,200" size="40,40" alphatest="blend" />
	</screen>
	"""

	def __init__(self, session, *args, **kwargs):
		Screen.__init__(self, session)
		self.skinName = "VuplusKexec"
		self.setTitle(_("Vu+ MultiBoot Manager"))
		self["labe14"] = StaticText(_("Press Green key to enable MultiBoot."))
		self["key_red"] = StaticText(_(" "))
		self["key_green"] = StaticText(_("Init Vu+ MultiBoot"))
		self["key_yellow"] = StaticText(" ")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"red": self.close,
			"green": self.RootInit,
			"yellow": self.close,
			"ok": self.close,
			"cancel": self.close,
		}, -1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("VU+ MultiBoot Manager"))

	def RootInit(self):
		if SystemInfo["CanKexecVu"]:
			self.TITLE = _("Vu+ MultiBoot Inititialisation - will reboot after 10 seconds.")
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
			print("[VuplusKexec][RootInit] Kernel Root", getMachineMtdKernel(), "   ", getMachineMtdRoot()) 				
			cmdlist = []
			cmdlist.append("dd if=/dev/%s of=/zImage" % getMachineMtdKernel())						# backup old kernel
			cmdlist.append("dd if=/usr/bin/kernel_auto.bin of=/dev/%s" % getMachineMtdKernel())	# create new kernel
			cmdlist.append("mv /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")						# copy userroot routine
			cmdlist.append("sync; sleep 1; sync; sleep 1; sync") 			 
			Console().eBatch(cmdlist, self.RootInitEnd, debug=True)
		else:
			self.close()

	def RootInitEnd(self, *args, **kwargs):
		self.session.open(TryQuitMainloop, 2)

	def Reboot(self):
		self.session.open(TryQuitMainloop, 2)
