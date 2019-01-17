from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll
import NavigationInstance
from ServiceReference import ServiceReference
from enigma import iServiceInformation, iPlayableService
from string import upper
from Tools.Transponder import ConvertToHumanReadable
from os import rename, system

class BhStreamInfo(Poll, Converter, object):
	DUMMY = 0
	STREAMURL = 1
	STREAMTYPE = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type
		self.short_list = True
		Poll.__init__(self)
		self.poll_interval = 1000
		self.poll_enabled = True
		self.list = []
		if 'StreamUrl' in type:
			self.type = self.STREAMURL
		elif 'StreamType' in type:
			self.type = self.STREAMTYPE

	def streamtype(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playref:
			refstr = playref.toString()
			strtype = refstr.replace('%3a', ':')
			if '0.0.0.0:' in strtype and strtype.startswith('1:0:') or '127.0.0.1:' in strtype and strtype.startswith('1:0:') or 'localhost:' in strtype and strtype.startswith('1:0:'):
				return 'Internal Ts Relay'
			elif '%3a' in refstr and strtype.startswith('4097:0:'):
				return 'Non Ts Stream'
			elif '%3a' in refstr and strtype.startswith('1:0:'):
				return 'GStreamer'
			elif '%3a' in refstr and strtype.startswith('5001:0:'):
				return 'GstPlayer'
			elif '%3a' in refstr and strtype.startswith('5002:0:'):
				return 'ExtePlayer3'
			elif strtype.startswith('1:134:'):
				return 'Alternative'
			else:
				return ''

	def streamurl(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()		
		if playref:
			refstr = playref.toString()
			if '%3a' in refstr:
				strurl = refstr.split(':')
				streamurl = strurl[10].replace('%3a', ':').replace('http://', '').replace('https://', '').split('/1:0:')[0].split('//')[0].split('/')[0].split('@')[-1]
				return streamurl
			else:
				return ''

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ''

			if tp:
				tpinfo = ConvertToHumanReadable(tp)
			if not tp:
				tp = info.getInfoObject(iServiceInformation.sTransponderData)
				tpinfo = ConvertToHumanReadable(tp)
		if self.type == self.DUMMY:
			refstr = str(self.reference())
			if '%3a' in refstrr:
				return self.streamurl()
				return ''
		else:
			if self.type == self.STREAMURL:
				return str(self.streamurl())
			if self.type == self.STREAMTYPE:
				return str(self.streamtype())

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evUpdatedInfo or what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
