from enigma import eLabel, eWidget, eSlider, fontRenderClass, ePoint, eSize
from Components.GUIComponent import GUIComponent
import skin


class ScrollLabel(GUIComponent):
	def __init__(self, text="", showscrollbar=True):
		GUIComponent.__init__(self)
		self.message = text
		self.showscrollbar = showscrollbar
		self.instance = None
		self.long_text = None
		self.right_text = None
		self.scrollbar = None
		self.TotalTextHeight = 0
		self.curPos = 0
		self.pageHeight = 0
		self.column = 0
		self.split = False
		self.splitchar = "|"
		self.keepsplitchar = 0
		self.onSelectionChanged = []

	def applySkin(self, desktop, parent):
		scrollbarWidth = skin.applySlider(self.scrollbar, 10, 1)
		ret = False
		if self.skinAttributes:
			widget_attribs = []
			scrollbar_attribs = []
			scrollbarAttrib = ["borderColor", "borderWidth", "scrollbarSliderForegroundColor", "scrollbarSliderBorderColor"]
			for (attrib, value) in self.skinAttributes[:]:
				if attrib == "scrollbarMode":
					if value == "showNever":
						self.showscrollbar = False
					else:
						self.showscrollbar = True
					self.skinAttributes.remove((attrib, value))
				elif attrib in scrollbarAttrib:
					scrollbar_attribs.append((attrib, value))
					self.skinAttributes.remove((attrib, value))
				elif attrib in ("scrollbarSliderPicture", "sliderPixmap"):
					self.scrollbar.setPixmap(skin.loadPixmap(value, desktop))
					self.skinAttributes.remove((attrib, value))
				elif attrib in ("scrollbarBackgroundPicture", "scrollbarbackgroundPixmap"):
					self.scrollbar.setBackgroundPixmap(skin.loadPixmap(value, desktop))
					self.skinAttributes.remove((attrib, value))
				elif attrib in ("transparent", "backgroundColor"):
					widget_attribs.append((attrib, value))
				elif attrib == "scrollbarWidth":
					scrollbarWidth = skin.parseScale(value)
					self.skinAttributes.remove((attrib, value))
				elif attrib == "scrollbarSliderBorderWidth":
					self.scrollbar.setBorderWidth(skin.parseScale(value))
					self.skinAttributes.remove((attrib, value))
				elif attrib == "split":
					self.split = 1 if value.lower() in ("1", "enabled", "on", "split", "true", "yes") else 0
					if self.split:
						self.right_text = eLabel(self.instance)
					self.skinAttributes.remove((attrib, value))
				elif attrib == "colposition":
					self.column = skin.parseScale(value)
					self.skinAttributes.remove((attrib, value))
				elif attrib == "dividechar":
					self.splitchar = value
					self.skinAttributes.remove((attrib, value))
				elif attrib == "keepdivchar":
					self.keepsplitchar = 1 if value.lower() in ("1", "enabled", "on", "keep", "true", "yes") else 0
					self.skinAttributes.remove((attrib, value))

			if self.split:
				skin.applyAllAttributes(self.long_text, desktop, self.skinAttributes + [("halign", "left")], parent.scale)
				skin.applyAllAttributes(self.right_text, desktop, self.skinAttributes + [("transparent", "1"), ("halign", "left" if self.column else "right")], parent.scale)
			else:
				skin.applyAllAttributes(self.long_text, desktop, self.skinAttributes, parent.scale)
			skin.applyAllAttributes(self.instance, desktop, widget_attribs, parent.scale)
			skin.applyAllAttributes(self.scrollbar, desktop, scrollbar_attribs + widget_attribs, parent.scale)
			ret = True
		self.pageWidth = self.long_text.size().width()
		lineheight = fontRenderClass.getInstance().getLineHeight(self.long_text.getFont()) or 30  # assume a random lineheight if nothing is visible
		lines = int(self.long_text.size().height() // lineheight)
		self.pageHeight = int(lines * lineheight)
		self.instance.move(self.long_text.position())
		self.instance.resize(eSize(self.pageWidth, self.pageHeight + int(lineheight // 6)))
		self.scrollbar.move(ePoint(self.pageWidth - scrollbarWidth, 0))
		self.scrollbar.resize(eSize(scrollbarWidth, self.pageHeight + int(lineheight // 6)))
		self.scrollbar.setOrientation(eSlider.orVertical)
		self.scrollbar.setRange(0, 100)
		self.setText(self.message)
		return ret

	def setPos(self, pos):
		self.curPos = max(0, min(pos, self.TotalTextHeight - self.pageHeight))
		self.long_text.move(ePoint(0, -self.curPos))
		self.split and self.right_text.move(ePoint(self.column, -self.curPos))
		self.selectionChanged()

	def setText(self, text, showBottom=False):
		self.message = text
		text = text.rstrip()
		if self.pageHeight:
			if self.split:
				left = []
				right = []
				for line in text.split("\n"):
					line = line.split(self.splitchar, 1)
					if self.keepsplitchar and len(line) > 1:
						line[0] += self.splitchar
					left.append(line[0])
					right.append("" if len(line) < 2 else line[1].lstrip())
				self.long_text.setText("\n".join(left))
				self.right_text.setText("\n".join(right))
			else:
				self.long_text.setText(text)
			self.TotalTextHeight = self.long_text.calculateSize().height()
			self.long_text.resize(eSize(self.pageWidth - 30, self.TotalTextHeight))
			self.split and self.right_text.resize(eSize(self.pageWidth - self.column - 30, self.TotalTextHeight))
			if showBottom:
				self.lastPage()
			else:
				self.setPos(0)
			if self.showscrollbar and self.TotalTextHeight > self.pageHeight:
				self.scrollbar.show()
				self.updateScrollbar()
			else:
				self.scrollbar.hide()

	def appendText(self, text, showBottom=True):
		self.setText(self.message + text, showBottom)

	def pageUp(self):
		if self.TotalTextHeight > self.pageHeight:
			self.setPos(self.curPos - self.pageHeight)
			self.updateScrollbar()

	def pageDown(self):
		if self.TotalTextHeight > self.pageHeight:
			self.setPos(self.curPos + self.pageHeight)
			self.updateScrollbar()

	def firstPage(self):
		self.setPos(0)
		self.updateScrollbar()

	def lastPage(self):
		self.setPos(self.TotalTextHeight - self.pageHeight)
		self.updateScrollbar()

	def isAtLastPage(self):
		return self.TotalTextHeight <= self.pageHeight or self.curPos == self.TotalTextHeight - self.pageHeight

	def updateScrollbar(self):
		vis = max(100 * self.pageHeight // self.TotalTextHeight, 3)
		start = (100 - vis) * self.curPos // ((self.TotalTextHeight - self.pageHeight) or 1)
		self.scrollbar.setStartEnd(start, start + vis)

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		self.scrollbar = eSlider(self.instance)
		self.long_text = eLabel(self.instance)

	def GUIdelete(self):
		self.long_text = None
		self.scrollbar = None
		self.instance = None
		self.right_text = None

	def getText(self):
		return self.message

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()
