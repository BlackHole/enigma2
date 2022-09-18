import sys

from enigma import ePythonOutput


class EnigmaLog:
	def __init__(self, level):
		self.level = level
		self.line = ""

	def write(self, data):
		if isinstance(data, bytes):
			data = data.decode(encoding="UTF-8", errors="ignore")
		self.line += data
		if "\n" in data:
			try:
				ePythonOutput(self.line, self.level)
			except TypeError:
				ePythonOutput("[RedirectOutput] The line below contains broken UTF-8\n", self.level)
				ePythonOutput(self.line.encode(encoding="UTF-8", errors="ignore").decode(), self.level)
			self.line = ""

	def flush(self):
		pass

	def isatty(self):
		return True


class EnigmaLogDebug(EnigmaLog):
	def __init__(self):
		EnigmaLog.__init__(self, 4)  # lvlDebug = 4


class EnigmaLogFatal(EnigmaLog):
	def __init__(self):
		EnigmaLog.__init__(self, 1)  # lvlError = 1


sys.stdout = EnigmaLogDebug()
sys.stderr = EnigmaLogFatal()
