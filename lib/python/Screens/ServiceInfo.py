from Components.GUIComponent import GUIComponent
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, eServiceCenter, eDVBFrontendParametersSatellite, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Tools.Transponder import ConvertToHumanReadable, getChannelNumber
from skin import applySkinFactor, parameters, parseFont, parseScale


TYPE_TEXT = 0
TYPE_VALUE_HEX = 1
TYPE_VALUE_DEC = 2
TYPE_VALUE_HEX_DEC = 3
TYPE_SLIDER = 4
TYPE_VALUE_ORBIT_DEC = 5
TYPE_VALUE_FREQ = 6
TYPE_VALUE_FREQ_FLOAT = 7
TYPE_VALUE_BITRATE = 8


def to_unsigned(x):
	return x & 0xFFFFFFFF


def ServiceInfoListEntry(a, b="", valueType=TYPE_TEXT, param=4, altColor=False):
	print("b:", b)
	if not isinstance(b, str):
		if valueType == TYPE_VALUE_HEX:
			b = ("%0" + str(param) + "X") % to_unsigned(b)
		elif valueType == TYPE_VALUE_FREQ:
			b = "%s MHz" % (b // 1000)
		elif valueType == TYPE_VALUE_FREQ_FLOAT:
			b = "%.3f MHz" % (b // 1000.0)
		elif valueType == TYPE_VALUE_BITRATE:
			b = "%s KSymbols/s" % (b // 1000)
		elif valueType == TYPE_VALUE_HEX_DEC:
			b = ("%0" + str(param) + "X (%d)") % (to_unsigned(b), b)
		elif valueType == TYPE_VALUE_ORBIT_DEC:
			direction = 'E'
			if b > 1800:
				b = 3600 - b
				direction = 'W'
			b = ("%d.%d%s") % (b // 10, b % 10, direction)
		else:
			b = str(b)
	xa, ya, wa, ha = parameters.get("ServiceInfoLeft", applySkinFactor(0, 0, 300, 25))
	xb, yb, wb, hb = parameters.get("ServiceInfoRight", applySkinFactor(300, 0, 600, 25))
	alignment = {"RT_HALIGN_LEFT": RT_HALIGN_LEFT, "RT_HALIGN_RIGHT": RT_HALIGN_RIGHT}
	leftColumnAlignment = alignment.get(parameters.get("ServiceInfoLeftColumnAlignment"), RT_HALIGN_LEFT)
	rightColumnAlignment = alignment.get(parameters.get("ServiceInfoRightColumnAlignment"), RT_HALIGN_LEFT)
	color = parameters.get("ServiceInfoAltColor", (0x00FFBF00)) # alternative foreground color
	res = [None]
	if b:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xa, ya, wa, ha, 0, leftColumnAlignment | RT_VALIGN_CENTER, a))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xb, yb, wb, hb, 0, rightColumnAlignment | RT_VALIGN_CENTER, b))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xa, ya, wa + wb, ha, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, a, color if altColor else None)) # spread horizontally
	return res


class ServiceInfoList(GUIComponent):
	def __init__(self, source):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = source
		self.l.setList(self.list)
		self.fontName = "Regular"
		self.fontSize = 23
		self.ItemHeight = 25

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.fontName = font.family
					self.fontSize = font.pointSize
				elif attrib == "itemHeight":
					self.ItemHeight = parseScale(value)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.setFontsize()
		self.l.setItemHeight(self.ItemHeight)
		return rc

	GUI_WIDGET = eListbox

	def setFontsize(self):
		self.l.setFont(0, gFont(self.fontName, self.fontSize))
		self.l.setFont(1, gFont(self.fontName, self.fontSize + 5))

	def postWidgetCreate(self, instance):
		self.instance.setContent(self.l)
		self.setFontsize()


TYPE_SERVICE_INFO = 1
TYPE_TRANSPONDER_INFO = 2


class ServiceInfo(Screen):
	def __init__(self, session, serviceref=None):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"red": self.close,
			"green": self.ShowECMInformation,
			"yellow": self.ShowServiceInformation,
			"blue": self.ShowTransponderInformation
		}, -1)

		self["infolist"] = ServiceInfoList([])
		self.setTitle(_("Service info"))
		self["key_red"] = self["red"] = Label(_("Exit"))

		self.transponder_info = self.info = self.service = self.feinfo = self.IPTV = None
		self.play_service = session.nav.getCurrentlyPlayingServiceReference()
		if serviceref and not (self.play_service and self.play_service == serviceref):
			self.type = TYPE_TRANSPONDER_INFO
			self.skinName = "ServiceInfoSimple"
			self.transponder_info = eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			# info is a iStaticServiceInformation, not a iServiceInformation
		else:
			self.type = TYPE_SERVICE_INFO
			self.service = session.nav.getCurrentService()
			if self.service:
				self.transponder_info = None
				self.info = self.service.info()
				self.feinfo = self.service.frontendInfo()
				if self.feinfo and not self.feinfo.getAll(True):
					self.feinfo = None
					serviceref = self.play_service
					self.transponder_info = serviceref and eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			if self.play_service:
				refstr = self.play_service.toString()
				reftype = self.play_service.type
				if "%3a//" in refstr and reftype not in (1, 257, 4098, 4114):
					self.IPTV = True
			if not self.IPTV:
				self["key_green"] = self["green"] = Label(_("ECM Info"))
				self["key_yellow"] = self["yellow"] = Label(_("Service & PIDs"))
			if self.feinfo or self.transponder_info:
				self["key_blue"] = self["blue"] = Label(_("Tuner setting values"))
			else:
				self.skinName = "ServiceInfoSimple"

		self.onShown.append(self.ShowServiceInformation)

	def ShowServiceInformation(self):
		if self.type == TYPE_SERVICE_INFO:
			self["Title"].text = _("Service info - service & PIDs")
			if self.feinfo or self.transponder_info:
				self["key_blue"].text = self["blue"].text = _("Tuner setting values")
			if self.session.nav.getCurrentlyPlayingServiceOrGroup():
				name = ServiceReference(self.play_service).getServiceName()
				refstr = self.play_service.toString()
				reftype = self.play_service.type
			else:
				name = _("N/A")
				refstr = _("N/A")
				reftype = 0
			resolution = "-"
			if self.info:
				from Components.Converter.PliExtraInfo import codec_data
				videocodec = codec_data.get(self.info.getInfo(iServiceInformation.sVideoType), "N/A")
				width = self.info.getInfo(iServiceInformation.sVideoWidth)
				height = self.info.getInfo(iServiceInformation.sVideoHeight)
				if width > 0 and height > 0:
					fps = (self.info.getInfo(iServiceInformation.sFrameRate) + 500) // 1000
					if fps in (0, -1):
						try:
							fps = (int(open("/proc/stb/vmpeg/0/framerate", "r").read()) + 500) // 1000
						except (ValueError, IOError):
							pass
					resolution = "%s - %dx%d - %s" % (videocodec, width, height, fps)
					resolution += ("i", "p", "")[self.info.getInfo(iServiceInformation.sProgressive)]
					aspect = self.getServiceInfoValue(iServiceInformation.sAspect)
					resolution += " - %s" % (aspect in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE) and "4:3" or "16:9")
				gamma = ("SDR", "HDR", "HDR10", "HLG", "")[self.info.getInfo(iServiceInformation.sGamma)]
				if gamma:
					resolution += " - %s" % gamma
			self.audio = self.service and self.service.audioTracks()
			self.numberofTracks = self.audio and self.audio.getNumberOfTracks() or 0
			fillList = [
				(_("Service name"), name, TYPE_TEXT),
				(_("Videocodec, size & format"), resolution, TYPE_TEXT),
				(_("Service reference"), ":".join(refstr.split(":")[:9]) if ":/" in refstr or "%3a//" in refstr else refstr, TYPE_TEXT)
			]
			if self.IPTV:  # IPTV 4097 5001, no PIDs shown
				fillList.append((_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT))
				if self.numberofTracks:
					t = self.audio.getCurrentTrack()
					audioDesc = self.audio.getTrackInfo(t).getDescription()
					audioLang = self.audio.getTrackInfo(t).getLanguage() or _("Not defined")
					fillList.append((_("Codec & lang"), "%s - %s" % (audioDesc, audioLang), TYPE_TEXT))
			else:
				if ":/" in refstr:  # mp4 videos, dvb-s-t recording
					fillList.append((_("Filename"), refstr.split(":")[10], TYPE_TEXT))
				else:  # fallback, movistartv, live dvb-s-t
					fillList.append((_("Provider"), self.getServiceInfoValue(iServiceInformation.sProvider), TYPE_TEXT))
					if "%3a//" in refstr:  # live dvb-s-t
						fillList.append((_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT))
				self.subList = self.getSubtitleList()
				self.togglePIDButton()
				fillList.extend([
					(_("Namespace & Orbital pos."), self.namespace(self.getServiceInfoValue(iServiceInformation.sNamespace)), TYPE_TEXT),
					(_("TSID"), self.getServiceInfoValue(iServiceInformation.sTSID), TYPE_VALUE_HEX_DEC, 4),
					(_("ONID"), self.getServiceInfoValue(iServiceInformation.sONID), TYPE_VALUE_HEX_DEC, 4),
					(_("Service ID"), self.getServiceInfoValue(iServiceInformation.sSID), TYPE_VALUE_HEX_DEC, 4),
					(_("Video PID"), self.getServiceInfoValue(iServiceInformation.sVideoPID), TYPE_VALUE_HEX_DEC, 4)
				])
				fillList += self.getTrackList()
				fillList.extend([
					(_("PCR PID"), self.getServiceInfoValue(iServiceInformation.sPCRPID), TYPE_VALUE_HEX_DEC, 4),
					(_("PMT PID"), self.getServiceInfoValue(iServiceInformation.sPMTPID), TYPE_VALUE_HEX_DEC, 4),
					(_("TXT PID"), self.getServiceInfoValue(iServiceInformation.sTXTPID), TYPE_VALUE_HEX_DEC, 4)
				])
				if self.showAll == True:
					fillList += self.subList

			self.fillList(fillList)
		elif self.transponder_info:
			self.fillList(self.getFEData(self.transponder_info))

	def namespace(self, nmspc):
		if isinstance(nmspc, str):
			return "N/A - N/A"
		namespace = "%08X" % (to_unsigned(nmspc))
		if namespace[:4] == "EEEE":
			return "%s - DVB-T" % (namespace)
		elif namespace[:4] == "FFFF":
			return "%s - DVB-C" % (namespace)
		else:
			EW = "E"
			posi = int(namespace[:4], 16)
			if posi > 1800:
				posi = 3600 - posi
				EW = "W"
		return "%s - %s\xb0 %s" % (namespace, (float(posi) / 10.0), EW)

	def getTrackList(self):
		trackList = []
		if self.numberofTracks:
			currentTrack = self.audio.getCurrentTrack()
			for i in range(0, self.numberofTracks):
				audioDesc = self.audio.getTrackInfo(i).getDescription()
				audioPID = self.audio.getTrackInfo(i).getPID()
				audioLang = self.audio.getTrackInfo(i).getLanguage()
				if audioLang == "":
					audioLang = _("Not defined")
				if self.showAll or currentTrack == i:
					trackList += [(_("Audio PID%s, codec & lang") % ((" %s") % (i + 1) if self.numberofTracks > 1 and self.showAll else ""), "%04X (%d) - %s - %s" % (to_unsigned(audioPID), audioPID, audioDesc, audioLang), TYPE_TEXT)]
				if self.getServiceInfoValue(iServiceInformation.sAudioPID) == "N/A":
					trackList = [(_("Audio PID, codec & lang"), "N/A - %s - %s" % (audioDesc, audioLang), TYPE_TEXT)]
		else:
			trackList = [(_("Audio PID"), "N/A", TYPE_TEXT)]
		return trackList

	def togglePIDButton(self):
		if (self["key_yellow"].text in (_("Service & PIDs"), _("Basic PID info"))) and (self.numberofTracks > 1 or self.subList):
			self.showAll = False
			self["key_yellow"].text = self["yellow"].text = _("Extended PID info")
			self["Title"].text = _("Service info - service & Basic PID Info")
		elif (self.numberofTracks < 2) and not self.subList:
			self.showAll = False
		else:
			self.showAll = True
			self["key_yellow"].text = self["yellow"].text = _("Basic PID info")
			self["Title"].text = _("Service info - service & Extended PID Info")

	def getSubtitleList(self):
		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		subList = []
		if subtitlelist:
			for x in subtitlelist:
				subNumber = str(x[1])
				subPID = x[1]
				subLang = ""
				subLang = x[4]

				if x[0] == 0:  # DVB PID
					subNumber = "%04X" % (x[1])
					subList += [(_("DVB Subtitles PID & lang"), "%04X (%d) - %s" % (to_unsigned(subPID), subPID, subLang), TYPE_TEXT)]

				elif x[0] == 1: # Teletext
					subNumber = "%x%02x" % (x[3] and x[3] or 8, x[2])
					subList += [(_("TXT Subtitles page & lang"), "%s - %s" % (subNumber, subLang), TYPE_TEXT)]

				elif x[0] == 2: # File
					types = (_("unknown"), _("embedded"), _("SSA file"), _("ASS file"),
							_("SRT file"), _("VOB file"), _("PGS file"))
					try:
						description = types[x[2]]
					except:
						description = _("unknown") + ": %s" % x[2]
					subNumber = str(int(subNumber) + 1)
					subList += [(_("Other Subtitles & lang"), "%s - %s - %s" % (subNumber, description, subLang), TYPE_TEXT)]
		return subList

	def ShowTransponderInformation(self):
		if self.type == TYPE_SERVICE_INFO and not self.IPTV:
			self["key_yellow"].text = self["yellow"].text = _("Service & PIDs")
			frontendData = self.feinfo and self.feinfo.getAll(True)
			if frontendData:
				if self["key_blue"].text == _("Tuner setting values"):
					self["Title"].text = _("Service info - tuner setting values")
					self["key_blue"].text = self["blue"].text = _("Tuner live values")
				else:
					self["Title"].text = _("Service info - tuner live values")
					self["key_blue"].text = self["blue"].text = _("Tuner setting values")
					frontendData = self.feinfo.getAll(False)
				self.fillList(self.getFEData(frontendData))
			elif self.transponder_info:
				self["Title"].text = _("Service info - tuner setting values")
				self["key_blue"].text = self["blue"].text = _("Tuner setting values")
				self.fillList(self.getFEData(self.transponder_info))

	def getFEData(self, frontendDataOrg):
		if frontendDataOrg and len(frontendDataOrg):
			frontendData = ConvertToHumanReadable(frontendDataOrg)
			if self.transponder_info:
				tuner = (_("Type"), frontendData["tuner_type"], TYPE_TEXT)
			else:
				tuner = (_("NIM & Type"), chr(ord('A') + frontendData["tuner_number"]) + " - " + frontendData["tuner_type"], TYPE_TEXT)
			if frontendDataOrg["tuner_type"] == "DVB-S":
				isMultistream = frontendData.get("is_id", eDVBFrontendParametersSatellite.No_Stream_Id_Filter) > eDVBFrontendParametersSatellite.No_Stream_Id_Filter
				t2mi = lambda x: None if x == -1 else str(x)
				return (tuner,
					(_("System & Modulation"), "%s %s" % (frontendData["system"], frontendData["modulation"]), TYPE_TEXT),
					(_("Orbital position"), "%s" % frontendData["orbital_position"], TYPE_TEXT),
					(_("Frequency & Polarization"), "%s - %s" % (frontendData.get("frequency", 0), frontendData["polarization"]), TYPE_TEXT),
					(_("Symbol rate & FEC"), "%s - %s" % (frontendData.get("symbol_rate", 0), frontendData["fec_inner"]), TYPE_TEXT),
					(_("Input Stream ID"), None if not isMultistream else "%s" % (frontendData.get("is_id", eDVBFrontendParametersSatellite.No_Stream_Id_Filter)), TYPE_TEXT),
					(_("PLS Mode & PLS Code"), None if not isMultistream else "%s - %s" % (frontendData["pls_mode"], frontendData["pls_code"]), TYPE_TEXT),
					(_("T2MI PLP ID"), t2mi(frontendData.get("t2mi_plp_id", eDVBFrontendParametersSatellite.No_T2MI_PLP_Id)), TYPE_TEXT),
					(_("T2MI PID"), None if frontendData.get("t2mi_plp_id", eDVBFrontendParametersSatellite.No_T2MI_PLP_Id) == eDVBFrontendParametersSatellite.No_T2MI_PLP_Id else str(frontendData.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)), TYPE_TEXT),
					(_("Inversion, Pilot & Roll-off"), "%s - %s - %s" % (frontendData["inversion"], frontendData.get("pilot", None), str(frontendData.get("rolloff", None))), TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-C":
				return (tuner,
					(_("Modulation"), "%s" % frontendData["modulation"], TYPE_TEXT),
					(_("Frequency"), "%s" % frontendData.get("frequency", 0), TYPE_TEXT),
					(_("Symbol rate & FEC"), "%s - %s" % (frontendData.get("symbol_rate", 0), frontendData["fec_inner"]), TYPE_TEXT),
					(_("Inversion"), "%s" % frontendData["inversion"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-T":
				return (tuner,
					(_("Frequency & Channel"), "%s - Ch. %s" % (frontendData.get("frequency", 0), getChannelNumber(frontendData["frequency"], frontendData["tuner_number"])), TYPE_TEXT),
					(_("Inversion & Bandwidth"), "%s - %s" % (frontendData["inversion"], frontendData["bandwidth"]), TYPE_TEXT),
					(_("Code R. LP-HP & Guard Int"), "%s - %s - %s" % (frontendData["code_rate_lp"], frontendData["code_rate_hp"], frontendData["guard_interval"]), TYPE_TEXT),
					(_("Constellation & FFT mode"), "%s - %s" % (frontendData["constellation"], frontendData["transmission_mode"]), TYPE_TEXT),
					(_("Hierarchy info"), "%s" % frontendData["hierarchy_information"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "ATSC":
				return (tuner,
					(_("System & Modulation"), "%s - %s" % (frontendData["system"], frontendData["modulation"]), TYPE_TEXT),
					(_("Frequency"), "%s" % frontendData.get("frequency", 0), TYPE_TEXT),
					(_("Inversion"), "%s" % frontendData["inversion"], TYPE_TEXT))
		return []

	def fillList(self, Labels):
		tlist = []
		for item in Labels:
			if item[1]:
				value = item[1]
				if len(item) < 4:
					tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2]))
				else:
					tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2], item[3]))
		self["infolist"].l.setList(tlist)

	def getServiceInfoValue(self, what):
		if self.info:
			v = self.info.getInfo(what)
			if v == -2:
				v = self.info.getInfoString(what)
			elif v == -1:
				v = _("N/A")
			return v
		return ""

	def ShowECMInformation(self):
		if self.info and not self.IPTV:
			from Components.Converter.PliExtraInfo import caid_data
			self["Title"].text = _("Service info - ECM Info")
			self["key_yellow"].text = self["yellow"].text = _("Service & PIDs")
			tlist = []
			for caid in sorted(set(self.info.getInfoObject(iServiceInformation.sCAIDPIDs)), key=lambda x: (x[0], x[1])):
				CaIdDescription = _("Undefined")
				extra_info = ""
				provid = ""
				for caid_entry in caid_data:
					if int(caid_entry[0], 16) <= caid[0] <= int(caid_entry[1], 16):
						CaIdDescription = caid_entry[2]
						break
				if caid[2]:
					if CaIdDescription == "Seca":
						provid = ",".join([caid[2][i:i + 4] for i in range(0, len(caid[2]), 30)])
					if CaIdDescription == "Nagra":
						provid = caid[2][-4:]
					if CaIdDescription == "Via":
						provid = caid[2][-6:]
					if provid:
						extra_info = "provid=%s" % provid
					else:
						extra_info = "extra data=%s" % caid[2]
				from Tools.GetEcmInfo import GetEcmInfo
				ecmdata = GetEcmInfo().getEcmData()
				formatstring = "ECMPid %04X (%d) %04X-%s %s"
				altColor = False
				if caid[0] == int(ecmdata[1], 16) and (caid[1] == int(ecmdata[3], 16) or str(int(ecmdata[2], 16)) in provid):
					formatstring = "%s (%s)" % (formatstring, _("active"))
					altColor = True
				tlist.append(ServiceInfoListEntry(formatstring % (caid[1], caid[1], caid[0], CaIdDescription, extra_info), altColor=altColor))
			if not tlist:
				tlist.append(ServiceInfoListEntry(_("No ECMPids available (FTA Service)")))
			self["infolist"].l.setList(tlist)
