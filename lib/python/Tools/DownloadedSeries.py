"""Support for downloaded (not recorded) TV series episodes in the movie list.

Recordings made by enigma2 always have a ".meta" file next to them, so a video
file without one is treated as downloaded. For those files this module can:

- work out the series title from the file name (e.g. "Show.Name.S01E02.mkv"),
so the movie list can group the episodes into a collection, together with
recordings of the same show;
- optionally look the episode up on TVMaze in a background thread and save the
result as a standard enigma2 ".eit" file, which the existing C++ service code
then reads like the .eit of a recording.
"""

from html import unescape
from json import loads
from os import path, remove, replace, stat
from queue import Queue
from re import IGNORECASE, compile as reCompile, sub
from string import capwords
from struct import pack
from threading import Lock, Thread
from time import gmtime, sleep
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VIDEO_EXTENSIONS = frozenset((".mp4", ".mkv", ".m4v", ".avi", ".mov", ".ts", ".webm", ".mpg", ".mpeg", ".wmv"))

# "Show.Name.S01E02", "Show Name - 1x02", "Show Name Series 1 Episode 2". A bare
# "Part 2" or "Episode 2" is deliberately not accepted: it matches too many films.
EPISODE_PATTERN = reCompile(
	r"^(?P<show>.+?)[\s._-]+(?:"
	r"s(?P<s1>\d{1,2})[\s._-]?e(?P<e1>\d{1,3})"  # S01E02, S01.E02
	r"|(?P<s2>\d{1,2})x(?P<e2>\d{1,3})"  # 1x02
	r"|(?:series|season)[\s._-]*(?P<s3>\d{1,2})[\s._-]*(?:episode|ep)[\s._-]*(?P<e3>\d{1,3})"  # Series 1 Episode 2
	r")(?!\d)",
	IGNORECASE)
BRACKETED_PATTERN = reCompile(r"\[[^\]]*\]|\{[^}]*\}")
TRAILING_YEAR_PATTERN = reCompile(r"[\s(]+(?:19|20)\d{2}\)?$")

TVMAZE_URL = "https://api.tvmaze.com/singlesearch/shows"
REQUEST_TIMEOUT = 10  # Seconds.
REQUEST_INTERVAL = 0.6  # Seconds between requests, TVMaze allows 20 requests per 10 seconds.
USER_AGENT = "enigma2-movielist"
EIT_READ_LIMIT = 4096  # eServiceEvent::parseFrom() reads at most this many bytes.


def parseEpisode(fileName):
	"""Return (show, season, episode) for an episode file name, or None."""
	base = path.splitext(path.basename(fileName))[0]
	base = BRACKETED_PATTERN.sub(" ", base).strip()
	match = EPISODE_PATTERN.match(base)
	if not match:
		return None
	show = sub(r"[._]+", " ", match.group("show"))
	show = TRAILING_YEAR_PATTERN.sub("", show)
	show = sub(r"\s+", " ", show).strip(" -:")
	if not show:
		return None
	if show.islower():
		show = capwords(show)
	season = int(match.group("s1") or match.group("s2") or match.group("s3"))
	episode = int(match.group("e1") or match.group("e2") or match.group("e3"))
	return show, season, episode


def isDownloadedVideo(filePath):
	"""True for a video file that was not recorded by enigma2 (no .meta file)."""
	return bool(filePath) and path.splitext(filePath)[1].lower() in VIDEO_EXTENSIONS and not path.exists(filePath + ".meta")


def getDownloadedSeriesTitle(filePath):
	"""Series title of a downloaded episode, or None if the file is not one."""
	if not filePath:
		return None
	parsed = parseEpisode(filePath)  # Cheap regex first, the file system check only for matches.
	if parsed and isDownloadedVideo(filePath):
		return parsed[0]
	return None


def eitPathFor(filePath):
	return path.splitext(filePath)[0] + ".eit"


# EIT file creation. The layout is the same as eEPGCache::saveEventToFile() writes
# for recordings: one EIT event (12 byte header + descriptor loop), no section header.

def _dvbText(text, maxBytes):
	"""Encode as DVB UTF-8 text (0x15 prefix), truncated on a character boundary."""
	data = text.encode("utf-8")[:maxBytes - 1].decode("utf-8", "ignore").encode("utf-8")
	return b"\x15" + data


def _splitUtf8(text, chunkBytes):
	"""Split text into UTF-8 chunks of at most chunkBytes without breaking a character."""
	chunks = []
	current = b""
	for char in text:
		encoded = char.encode("utf-8")
		if len(current) + len(encoded) > chunkBytes:
			chunks.append(current)
			current = b""
		current += encoded
	if current:
		chunks.append(current)
	return chunks


def _bcd(value):
	return ((value // 10) << 4) | (value % 10)


def buildEit(eventName, shortText, extendedText, begin, duration=0, eventId=1, language=b"eng"):
	utc = gmtime(begin)
	year, month, day = utc.tm_year - 1900, utc.tm_mon, utc.tm_mday
	leap = 1 if month <= 2 else 0
	mjd = 14956 + day + int((year - leap) * 365.25) + int((month + 1 + leap * 12) * 30.6001)
	duration = max(0, min(int(duration), 99 * 3600 + 59 * 60 + 59))
	hours, rest = divmod(duration, 3600)
	minutes, seconds = divmod(rest, 60)

	# Short event descriptor (0x4D): language(3) + name length(1) + name + text length(1) + text <= 255.
	name = _dvbText(eventName, 120)
	text = _dvbText(shortText, 255 - 5 - len(name))
	payload = language + bytes((len(name),)) + name + bytes((len(text),)) + text
	descriptors = bytes((0x4D, len(payload))) + payload

	# Extended event descriptors (0x4E): number/last(1) + language(3) + items length(1) + text length(1) + text <= 255.
	# Each chunk is decoded separately by enigma2, so each one needs its own 0x15 prefix.
	space = EIT_READ_LIMIT - 12 - len(descriptors)
	maxChunks = min(16, space // 257)  # 4 bit descriptor numbers, and stay inside the read limit.
	chunks = _splitUtf8(extendedText, 248)[:maxChunks]
	for number, chunk in enumerate(chunks):
		chunk = b"\x15" + chunk
		payload = bytes(((number << 4) | (len(chunks) - 1),)) + language + b"\x00" + bytes((len(chunk),)) + chunk
		descriptors += bytes((0x4E, len(payload))) + payload

	header = pack(">HHBBBBBBH", eventId & 0xFFFF, mjd, _bcd(utc.tm_hour), _bcd(utc.tm_min), _bcd(utc.tm_sec), _bcd(hours), _bcd(minutes), _bcd(seconds), (4 << 13) | len(descriptors))  # Running status 4 = running.
	return header + descriptors


# TVMaze lookup, done on a single background thread.

class EpisodeInfoFetcher:
	def __init__(self):
		self.queue = Queue()
		self.lock = Lock()
		self.seen = set()  # Files queued this session, so a failed lookup is not repeated on every list reload.
		self.shows = {}  # Lower case show name -> TVMaze show dict with embedded episodes, or None if not found.
		self.thread = None

	def request(self, filePath):
		if not filePath or path.exists(eitPathFor(filePath)):
			return
		with self.lock:
			if filePath in self.seen:
				return
			self.seen.add(filePath)
			if self.thread is None:
				self.thread = Thread(target=self.run, name="DownloadedSeriesEit", daemon=True)
				self.thread.start()
		self.queue.put(filePath)

	def run(self):
		while True:
			filePath = self.queue.get()
			try:
				self.process(filePath)
			except Exception as err:
				print("[DownloadedSeries] Episode lookup failed for '%s': %s" % (filePath, err))

	def process(self, filePath):
		parsed = parseEpisode(filePath)
		eitPath = eitPathFor(filePath)
		if not parsed or path.exists(eitPath) or not isDownloadedVideo(filePath):
			return
		show, season, episode = parsed
		showData = self.getShow(show)
		if not showData:
			return
		episodeData = None
		for candidate in showData.get("_embedded", {}).get("episodes", []):
			if candidate.get("season") == season and candidate.get("number") == episode:
				episodeData = candidate
				break
		if not episodeData:
			print("[DownloadedSeries] No TVMaze data for '%s' S%02dE%02d." % (show, season, episode))
			return
		title = "S%02dE%02d" % (season, episode)
		if episodeData.get("name"):
			title = "%s - %s" % (title, episodeData["name"])
		summary = unescape(sub(r"<[^>]+>", "", episodeData.get("summary") or "")).strip()
		duration = (episodeData.get("runtime") or showData.get("runtime") or 0) * 60
		if not path.exists(filePath):  # Deleted while we were waiting for the network.
			return
		data = buildEit(showData.get("name") or show, title, summary, stat(filePath).st_mtime, duration, episodeData.get("id") or 1)
		tempPath = eitPath + ".tmp"
		try:
			with open(tempPath, "wb") as fd:
				fd.write(data)
			replace(tempPath, eitPath)
		except OSError as err:
			print("[DownloadedSeries] Unable to write '%s': %s" % (eitPath, err))
			try:
				remove(tempPath)
			except OSError:
				pass

	def getShow(self, show):
		key = show.lower()
		if key in self.shows:
			return self.shows[key]
		sleep(REQUEST_INTERVAL)
		url = "%s?%s" % (TVMAZE_URL, urlencode({"q": show, "embed": "episodes"}))
		try:
			with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=REQUEST_TIMEOUT) as response:
				data = loads(response.read().decode("utf-8"))
		except HTTPError as err:
			if err.code != 404:  # Anything but "not found" (e.g. 429 rate limit) may work next time.
				raise
			data = None
		self.shows[key] = data  # Only cache answers, network errors raise above and are retried next session.
		return data


episodeInfoFetcher = EpisodeInfoFetcher()
