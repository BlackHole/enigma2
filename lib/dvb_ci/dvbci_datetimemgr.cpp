/* DVB CI DateTime Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_datetimemgr.h>

eDVBCIDateTimeSession::eDVBCIDateTimeSession():
	m_timer(eTimer::create(eApp)), m_interval(0)
{
	//CONNECT(m_timer->timeout, eDVBCIDateTimeSession::sendDateTime);
	m_timer->timeout.connect(sigc::mem_fun(*this, &eDVBCIDateTimeSession::sendDateTime));
}

int eDVBCIDateTimeSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eDebugNoNewLine("[CI DT] SESSION(%d)/DATETIME %02x %02x %02x: ", session_nb, tag[0],tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebugNoNewLine("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x84))
	{
		switch (tag[2])
		{
		case 0x40:
			m_timer->stop();
			m_interval = (data && len) ? ((unsigned char *)data)[0] : 0;
			state=stateSendDateTime;
			return 1;
			break;
		default:
			eDebug("[CI DT] unknown APDU tag 9F 84 %02x", tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCIDateTimeSession::doAction()
{
	switch (state)
	{
	case stateStarted:
		return 0;
	case stateSendDateTime:
		sendDateTime();
		return 0;
	case stateFinal:
		eDebug("[CI DT] stateFinal and action should not happen");
		[[fallthrough]];
	default:
		return 0;
	}
}

void eDVBCIDateTimeSession::sendDateTime()
{
	unsigned char tag[3]={0x9f, 0x84, 0x41}; // date_time_response
	unsigned char msg[6];
	time_t tv = time(NULL); // TODO maybe move unixtime to dvbtime in lib/dvb/dvbtime
	uint16_t mjd = tv / 86400 + 40587; // mjd 01.01.1970 is 40587
	tv %= 86400;
	uint8_t hh = tv / 3600;
	tv %= 3600;
	uint8_t mm = tv / 60;
	tv %= 60;
	uint8_t ss = tv;

	msg[0] = 5; // not using offset
	msg[1] = (mjd >> 8) & 0xff;
	msg[2] = mjd & 0xff;
	msg[3] = ((hh / 10) << 4) | (hh % 10);
	msg[4] = ((mm / 10) << 4) | (mm % 10);
	msg[5] = ((ss / 10) << 4) | (ss % 10);

	sendAPDU(tag, msg, 6);

	if (m_interval > 0)
	{
		m_timer->startLongTimer(m_interval);
	}
}
