from enigma import iPlayableService

from Components.config import config
from Screens.MessageBox import MessageBox
from Tools import Notifications


class SoftCSANotify:
	"""Shows what software descrambling is doing with late control words.

	The numbers are in the debug log; on screen only what the viewer notices.
	"""

	DELAY = "softcsa-delay"
	BADKEY = "softcsa-badkey"
	SECONDS = 5

	def __init__(self):
		self.session = None
		self.limitShown = False

	def setSession(self, session):
		self.session = session
		session.nav.event.append(self.serviceEvent)

	def serviceEvent(self, event):
		match event:
			case iPlayableService.evStart:
				# Another service, so its state has still to be learnt.
				self.limitShown = False
			case iPlayableService.evDmxcsaDelayRaised:
				self.showPopup(_("A control word arrived too late, playback is now delayed further"), MessageBox.TYPE_INFO, self.DELAY)
			case iPlayableService.evDmxcsaDelayLimit:
				# Saying it again changes nothing: the delay stays where it is.
				if not self.limitShown:
					self.limitShown = True
					self.showPopup(_("A control word arrived too late, playback cannot be delayed further"), MessageBox.TYPE_WARNING, self.DELAY)
			case iPlayableService.evDmxcsaBadCw:
				# A fault at the card or the server, not a state of our own.
				self.showPopup(_("The control word received does not open this channel"), MessageBox.TYPE_ERROR, self.BADKEY)

	def showPopup(self, text, popupType, popupId):
		if config.misc.softcsa.notifications.value:
			Notifications.AddPopup(text=text, type=popupType, timeout=self.SECONDS, id=popupId)


softCSANotify = SoftCSANotify()


def initSoftCSANotify(session):
	softCSANotify.setSession(session)
