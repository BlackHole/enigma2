from Components.Sources.Source import Source
from Components.Element import cached
from enigma import eServiceCenter


class ServiceEvent(Source):
	def __init__(self):
		Source.__init__(self)
		self.service = None
		self.additionalInfo = None

	@cached
	def getCurrentService(self):
		return self.service

	@cached
	def getCurrentEvent(self):
		evt = None
		if self.service:
			from Components.MovieList import getLocalEitEvent
			evt = getLocalEitEvent(self.service, self.additionalInfo)
		if evt is None:
			evt = self.service and self.info and self.info.getEvent(self.service)
		return evt

	@cached
	def getInfo(self):
		return self.service and eServiceCenter.getInstance().info(self.service)

	event = property(getCurrentEvent)
	info = property(getInfo)

	def newService(self, ref, additionalInfo=None):
		self.service = ref
		self.additionalInfo = additionalInfo
		if not ref:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))
