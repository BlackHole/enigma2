installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder CableScan \
	VideoTune Hotplug OpentvZapper \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoClippingSetup VideoEnhancement \
	WirelessLan NetworkWizard SABnzbdSetup \
	FastScan SatelliteEquipmentControl DiseqcTester \
	FastChannelChange

if HAVE_LIBVUGLES2
SUBDIRS += AnimationSetup
endif

if HAVE_OSDANIMATION
SUBDIRS += AnimationSetup
endif

install_PYTHON = __init__.py
