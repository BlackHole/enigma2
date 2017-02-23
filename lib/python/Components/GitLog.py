import urllib, socket
from sys import modules
from os import path
from boxbranding import getImageType, getFeedsUrl

def fetchlog(logtype):
	releasenotes = ""
	try:
		sourceurl = "%s/%s-git.log" % (getFeedsUrl().rsplit("/", 1)[0], logtype)
		print "[GitLog]",sourceurl
		sourcefile,headers = urllib.urlretrieve(sourceurl)
		fd = open(sourcefile, 'r')
		for line in fd.readlines():
			if getImageType() == 'release' and line.startswith('openbh: developer'):
				print '[GitLog] Skipping dev line'
				continue
			elif getImageType() == 'developer' and line.startswith('openbh: release'):
				print '[GitLog] Skipping release line'
				continue
			releasenotes += line
		fd.close()
		releasenotes = releasenotes.replace('\nopenbh: build',"\n\nopenbh: build")
		releasenotes = releasenotes.replace('\nopenbh: %s' % getImageType(),"\n\nopenbh: %s" % getImageType())
	except:
		releasenotes = '404 Not Found'
	return releasenotes

# For modules that do "from GitLog import gitlog"
gitlog = modules[__name__]
