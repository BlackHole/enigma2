"""Support for downloaded (not recorded) TV series episodes in the movie list.

Recordings made by enigma2 always have a ".meta" file with the recorded
service in it, so a video file without one is treated as downloaded. For
those files this module can:

- work out the series title from the file name (e.g. "Show.Name.S01E02.mkv"),
so the movie list can group the episodes into a collection, together with
recordings of the same show;
- optionally look the episode up on TVMaze in a background thread and save the
result as a standard enigma2 ".eit" file, which the existing C++ service code
then reads like the .eit of a recording.
"""

from html import unescape
from json import loads
from os import listdir, path, rename, remove, replace, stat
from queue import Queue
from re import IGNORECASE, compile as reCompile, sub
from string import capwords
from struct import pack
from threading import Lock, Thread
from time import gmtime, sleep, time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VIDEO_EXTENSIONS = frozenset((".mp4", ".mkv", ".m4v", ".avi", ".mov", ".ts", ".webm", ".mpg", ".mpeg", ".wmv"))

# "Show.Name.S01E02", "Show Name - 1x02", "Show Name Series 1 Episode 2" and,
# without a season, "Show Name - Ep4", "Show Name Episode 4" or "Show Name Part 2".
EPISODE_PATTERN = reCompile(
	r"^(?P<show>.+?)[\s._-]+(?:"
	r"s(?P<s1>\d{1,2})[\s._-]?e(?P<e1>\d{1,3})"  # S01E02, S01.E02
	r"|(?P<s2>\d{1,2})x(?P<e2>\d{1,3})"  # 1x02
	r"|(?:series|season)[\s._-]*(?P<s3>\d{1,2})[\s._-]*(?:episode|ep|part)[\s._-]*(?P<e3>\d{1,3})"  # Series 1 Episode 2
	r"|(?:episode|ep|part)[\s._-]*(?P<e4>\d{1,3})"  # Ep4, Episode 4, Part 2 (season unknown)
	r")(?!\d)",
	IGNORECASE)
BRACKETED_PATTERN = reCompile(r"\[[^\]]*\]|\{[^}]*\}")
# Language codes catch-up and IPTV services put in front of titles ("EN Show Name").
LANGUAGE_CODES = ("EN", "UK", "US", "AU", "CA", "FR", "DE", "ES", "IT", "AR")
# For renaming files the code has to be in capitals, so "It Follows.mp4" or "Us.mp4" are left alone.
# Any "|", ":" or "-" after the code is removed too: "EN | Show.mp4", "EN: Show.mp4", "EN - Show.mp4".
FILE_LANGUAGE_PREFIX_PATTERN = reCompile(r"^(?:%s)(?:\s*[|:-]+\s*|\s+)(?=\S)" % "|".join(LANGUAGE_CODES))
RENAME_SETTLE_TIME = 120  # Seconds a file has to be unchanged before it is renamed, so a download in progress is left alone.

RECORDING_NAME_PREFIX_PATTERN = reCompile(r"^\d{8}\s+\d{4}\s+-\s+[^-]+-\s+")  # "20261114 2057 - BBC One HD - "

# Cleaning of the show name before it is searched on TVMaze. The collection name
# keeps these (recordings have the same prefixes), only the search drops them.
SEARCH_PREFIX_PATTERN = reCompile(r"^(?:all\s+new|brand\s+new|new|premiere|live|repeat)\s*:\s*", IGNORECASE)
SEARCH_LANGUAGE_PATTERN = reCompile(r"^(?:%s)\s+" % "|".join(LANGUAGE_CODES), IGNORECASE)
SEARCH_BRACKETS_PATTERN = reCompile(r"\[[^\]]*\]|\([^\)]*\)")
SEARCH_RELEASE_TAGS_PATTERN = reCompile(
	r"\b(?:2160p|1080p|1080i|720p|576p|480p|4k|uhd|fhd|hd|sd|"
	r"web[- ]?dl|web[- ]?rip|web|hdtv|pdtv|dvdrip|bdrip|brrip|bluray|blu[- ]?ray|remux|"
	r"x264|x265|h\.?264|h\.?265|hevc|avc|xvid|divx|av1|"
	r"aac(?:2\.0)?|ac3|eac3|ddp?5\.1|dd5\.1|dts(?:-hd)?|atmos|mp3|flac|"
	r"10bit|8bit|hdr10?\+?|dv|dolby\s*vision|sdr|"
	r"proper|repack|rerip|internal|extended|uncut|uncensored|director'?s\s*cut|multi|dual\s*audio)\b.*$",
	IGNORECASE)
SEARCH_YEARS_PATTERN = reCompile(r"(?:\s+\(?\d{4}\)?)+")

TVMAZE_API = "https://api.tvmaze.com"
REQUEST_TIMEOUT = 10  # Seconds.
REQUEST_INTERVAL = 0.6  # Seconds between requests, TVMaze allows 20 requests per 10 seconds.
USER_AGENT = "enigma2-movielist"
EIT_READ_LIMIT = 4096  # eServiceEvent::parseFrom() reads at most this many bytes.


def getSearchTitle(show):
	"""Show name as searched on TVMaze, without prefixes, language codes, release tags and years."""
	title = SEARCH_PREFIX_PATTERN.sub("", show)
	title = SEARCH_LANGUAGE_PATTERN.sub("", title)
	title = SEARCH_BRACKETS_PATTERN.sub(" ", title)
	title = SEARCH_RELEASE_TAGS_PATTERN.sub("", title)
	title = SEARCH_YEARS_PATTERN.sub("", title)
	title = sub(r"\s+", " ", title).strip(" -_:")
	return title or show


def parseEpisode(fileName):
	"""Return (show, season, episode) for an episode file name, or None.

	season is None when the file name only has an episode number.
	"""
	base = path.splitext(path.basename(fileName))[0]
	base = RECORDING_NAME_PREFIX_PATTERN.sub("", base.strip())
	base = BRACKETED_PATTERN.sub(" ", base).strip()
	match = EPISODE_PATTERN.match(base)
	if not match:
		return None
	show = sub(r"[._]+", " ", match.group("show"))
	show = sub(r"\s+", " ", show).strip(" -:")
	if not show:
		return None
	if show.islower():
		show = capwords(show)
	season = match.group("s1") or match.group("s2") or match.group("s3")
	season = int(season) if season else None
	episode = int(match.group("e1") or match.group("e2") or match.group("e3") or match.group("e4"))
	return show, season, episode


def isDownloadedVideo(filePath):
	"""True for a video file that was not recorded by enigma2."""
	if not filePath or path.splitext(filePath)[1].lower() not in VIDEO_EXTENSIONS:
		return False
	try:
		with open(filePath + ".meta", "r", encoding="utf-8", errors="ignore") as fd:
			serviceRef = fd.readline().strip()
	except OSError:
		return True  # No .meta file.
	# enigma2 also writes a .meta for a .ts file it did not record, e.g. when
	# eStaticServiceDVBPVRInformation::getLength() caches the length. That one
	# has an empty service reference ("1:0:0:0:0:0:0:0:0:0:"), a recording has
	# a real one with a service id, transport stream id, network id or namespace.
	fields = serviceRef.split(":")
	return len(fields) < 7 or all(field in ("", "0") for field in fields[3:7])


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


def hasUsableEit(filePath):
	"""True if the file has an .eit that enigma2 can read.

	An earlier version of this feature wrote .eit files with a 14 byte EIT
	section header in front of the event (table id 0x4E, section syntax 0xF,
	service id 1, version byte 0xC1, ending in 00 4E). enigma2 reads an .eit
	from the first byte, so those files show nothing and are replaced.
	"""
	try:
		with open(eitPathFor(filePath), "rb") as fd:
			head = fd.read(14)
	except OSError:
		return False
	return not (len(head) == 14 and head[0] == 0x4E and head[1] & 0xF0 == 0xF0 and head[3:6] == b"\x00\x01\xC1" and head[12:14] == b"\x00\x4E")


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


def stripLanguagePrefixes(folder, skipPath=None):
	"""Remove a language code from the start of downloaded video file names.

	"EN | Show Name Season 1 Episode 2.mp4" becomes "Show Name Season 1 Episode 2.mp4".
	Side files with the same name (.eit, .srt, .meta, .cuts, ...) are renamed with it.
	Recordings, files still being written, skipPath (the file playing now) and renames
	that would overwrite an existing file are skipped. Returns True if anything was renamed.
	"""
	try:
		entries = listdir(folder)
	except OSError:
		return False
	now = time()
	done = set()
	renamed = False
	for entry in entries:
		match = FILE_LANGUAGE_PREFIX_PATTERN.match(entry)
		if not match or entry in done or entry[match.end():].startswith("."):  # Nothing but the code before the extension.
			continue
		filePath = path.join(folder, entry)
		if filePath == skipPath or not isDownloadedVideo(filePath):
			continue
		try:
			if now - stat(filePath).st_mtime < RENAME_SETTLE_TIME:
				continue
		except OSError:
			continue
		stem = path.splitext(entry)[0] + "."
		group = [x for x in entries if x.startswith(stem) and x not in done]
		targets = [x[match.end():] for x in group]
		if any(path.exists(path.join(folder, x)) for x in targets):
			print("[DownloadedSeries] Not renaming '%s', a file without the language code already exists." % entry)
			continue
		for old, new in zip(group, targets):
			try:
				rename(path.join(folder, old), path.join(folder, new))
				renamed = True
			except OSError as err:
				print("[DownloadedSeries] Unable to rename '%s': %s" % (old, err))
			done.add(old)
	return renamed


# TVMaze lookup, done on a single background thread.

class EpisodeInfoFetcher:
	def __init__(self):
		self.queue = Queue()
		self.lock = Lock()
		self.seen = set()  # Files queued this session, so a failed lookup is not repeated on every list reload.
		self.shows = {}  # Lower case show name -> TVMaze show dict with embedded episodes, or None if not found.
		self.thread = None

	def request(self, filePath):
		if not filePath or hasUsableEit(filePath):
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
		if not parsed or hasUsableEit(filePath) or not isDownloadedVideo(filePath):
			return
		show, season, episode = parsed
		showData = self.getShow(show)
		if not showData:
			return
		episodes = showData.get("_embedded", {}).get("episodes", [])
		candidates = [x for x in episodes if x.get("number") == episode and (season is None or x.get("season") == season)]
		if season is None and len(candidates) > 1:  # Episode number only and more than one season has it: assume season 1.
			candidates = [x for x in candidates if x.get("season") == 1]
		label = "Ep%d" % episode if season is None else "S%02dE%02d" % (season, episode)
		if not candidates:
			print("[DownloadedSeries] No TVMaze data for '%s' %s." % (show, label))
			return
		episodeData = candidates[0]
		if season is None:
			season = episodeData.get("season")
			label = "S%02dE%02d" % (season, episode) if isinstance(season, int) else label
		title = label
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
		query = getSearchTitle(show)
		try:
			data = self.getJson("singlesearch/shows", {"q": query, "embed": "episodes"})
		except HTTPError as err:
			if err.code != 404:  # Anything but "not found" (e.g. 429 rate limit) may work next time.
				raise
			# No exact match, take the best result of the fuzzy search and get its episodes.
			results = self.getJson("search/shows", {"q": query})
			data = results[0].get("show") if results else None
			if data and data.get("id"):
				data = self.getJson("shows/%d" % data["id"], {"embed": "episodes"})
		self.shows[key] = data  # Only cache answers, network errors raise above and are retried next session.
		return data

	def getJson(self, endpoint, parameters):
		sleep(REQUEST_INTERVAL)
		url = "%s/%s?%s" % (TVMAZE_API, endpoint, urlencode(parameters))
		with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=REQUEST_TIMEOUT) as response:
			return loads(response.read().decode("utf-8"))


episodeInfoFetcher = EpisodeInfoFetcher()
