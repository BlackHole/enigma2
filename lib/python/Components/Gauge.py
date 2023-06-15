from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Components.VariableValue import VariableValue

from enigma import eGauge


class Gauge(VariableValue, HTMLComponent, GUIComponent):
	def __init__(self):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

	GUI_WIDGET = eGauge

	def postWidgetCreate(self, instance):
		instance.setValue(10)

	def setValue(self, value):
		if self.instance is not None:
			self.instance.setValue(value)

	value = property(setValue)
