/* DVB CI Host Control Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_host_ctrl.h>

int eDVBCIHostControlSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eTraceNoNewLine("[CI HCTRL] SESSION(%d)/HCTRL %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLine("\n");
	if ((tag[0]==0x9f) && (tag[1]==0x84))
	{
		switch (tag[2])
		{
		default:
			eWarning("[CI HCTRL] unknown APDU tag 9F 84 %02x", tag[2]);
			break;
		}
	}

	return 0;
}

int eDVBCIHostControlSession::doAction()
{
	switch (state)
	{
	default:
		eWarning("[CI HCTRL] unknown state");
		break;
	}

	return 0;
}
