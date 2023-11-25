from Components.Converter.Converter import Converter
from Components.Element import cached
from Screens.InfoBarGenerics import whitelist
import NavigationInstance
from enigma import iPlayableService


class StreamInfo(Converter):
	STREAMURL = 0
	STREAMTYPE = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type
		if 'StreamUrl' in type:
			self.type = self.STREAMURL
		elif 'StreamType' in type:
			self.type = self.STREAMTYPE

	def streamtype(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playref:
			refstr = playref.toString()
			strtype = refstr.replace('%3a', ':')
			if strtype.startswith('1:0:'):
				if '0.0.0.0' in refstr or '127.0.0.1' in refstr or 'localhost' in refstr:
					return ''
				elif '%3a' in refstr:
					return 'GStreamer'
			elif '%3a' in refstr and strtype.startswith('4097:0:'):
				return 'MediaPlayer'
			elif '%3a' in refstr and strtype.startswith('5001:0:'):
				return 'GstPlayer'
			elif '%3a' in refstr and strtype.startswith('5002:0:'):
				return 'ExtePlayer3'
		return ''

	def streamurl(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playref:
			refstr = playref.toString()
			if '0.0.0.0' in refstr or '127.0.0.1' in refstr or 'localhost' in refstr:
				return ''
			elif '%3a' in refstr:
				strurl = refstr.split(':')
				streamurl = strurl[10].replace('%3a', ':').replace('http://', '').replace('https://', '').split('/1:0:')[0].split('//')[0].split('/')[0].split('@')[-1]
				return streamurl
		return ''

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if info:
			if self.type == self.STREAMURL:
				return str(self.streamurl())
			elif self.type == self.STREAMTYPE:
				return str(self.streamtype())
		return ''

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
