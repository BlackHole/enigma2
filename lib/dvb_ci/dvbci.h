#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#ifndef SWIG

#include <lib/base/ebase.h>
#include <lib/service/iservice.h>
#include <lib/python/python.h>
#include <set>
#include <queue>

#include <lib/network/serversocket.h>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCIMMISession;
class eDVBServicePMTHandler;
class eDVBCISlot;
class eDVBCIInterfaces;

struct queueData
{
	uint8_t prio;
	unsigned char *data;
	unsigned int len;
	queueData( unsigned char *data, unsigned int len, uint8_t prio = 0 )
		:prio(prio), data(data), len(len)
	{

	}
	bool operator < ( const struct queueData &a ) const
	{
		return prio < a.prio;
	}
};

typedef std::pair<std::string, uint32_t> providerPair;
typedef std::set<providerPair> providerSet;
typedef std::set<uint16_t> caidSet;
typedef std::set<eServiceReference> serviceSet;

class eDVBCISlot: public iObject, public sigc::trackable
{
	friend class eDVBCIInterfaces;
	DECLARE_REF(eDVBCISlot);
	int slotid;
	int fd;
	ePtr<eSocketNotifier> notifier;
	int state;
	std::map<uint16_t, uint8_t> running_services;
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCIMMISession *mmi_session;
	std::priority_queue<queueData> sendqueue;
	caidSet possible_caids;
	serviceSet possible_services;
	providerSet possible_providers;
	int use_count;
	eDVBCISlot *linked_next; // needed for linked CI handling
	std::string current_source;
	int current_tuner;
	bool user_mapped;
	void data(int);
	bool plugged;
public:
	enum {stateRemoved, stateInserted, stateInvalid, stateResetted};
	eDVBCISlot(eMainloop *context, int nr);
	~eDVBCISlot();

	int send(const unsigned char *data, size_t len);

	void setAppManager( eDVBCIApplicationManagerSession *session );
	void setMMIManager( eDVBCIMMISession *session );
	void setCAManager( eDVBCICAManagerSession *session );

	eDVBCIApplicationManagerSession *getAppManager() { return application_manager; }
	eDVBCIMMISession *getMMIManager() { return mmi_session; }
	eDVBCICAManagerSession *getCAManager() { return ca_manager; }

	int getState() { return state; }
	int getSlotID();
	int reset();
	int startMMI();
	int stopMMI();
	int answerText(int answer);
	int answerEnq(char *value);
	int cancelEnq();
	int getMMIState();
	int sendCAPMT(eDVBServicePMTHandler *ptr, const std::vector<uint16_t> &caids=std::vector<uint16_t>());
	void removeService(uint16_t program_number=0xFFFF);
	int getNumOfServices() { return running_services.size(); }
	int setSource(const std::string &source);
	int setClockRate(int);
	static std::string getTunerLetter(int tuner_no) { return std::string(1, char(65 + tuner_no)); }
};

struct CIPmtHandler
{
	eDVBServicePMTHandler *pmthandler;
	eDVBCISlot *cislot;
	CIPmtHandler()
		:pmthandler(NULL), cislot(NULL)
	{}
	CIPmtHandler( const CIPmtHandler &x )
		:pmthandler(x.pmthandler), cislot(x.cislot)
	{}
	CIPmtHandler( eDVBServicePMTHandler *ptr )
		:pmthandler(ptr), cislot(NULL)
	{}
	bool operator==(const CIPmtHandler &x) const { return x.pmthandler == pmthandler; }
};

typedef std::list<CIPmtHandler> PMTHandlerList;

#endif // SWIG

#ifndef SWIG
class eCIClient : public eUnixDomainSocket
{
	struct ciplus_header
	{
		unsigned int magic;
		unsigned int cmd;
		unsigned int size;
	}__attribute__((packed));

	struct ciplus_message
	{
		unsigned int slot;
		unsigned long idtag;
		unsigned char tag[4];
		unsigned int session;
		unsigned int size;
	}__attribute__((packed));

	unsigned int receivedLength;
	unsigned int receivedCmd;
	unsigned int receivedCmdSize;
	unsigned char *receivedData;

	ciplus_header header;
protected:
	eDVBCIInterfaces *parent;
	void connectionLost();
	void dataAvailable();
public:
	eCIClient(eDVBCIInterfaces *handler, int socket);
	void sendData(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len);

	enum
	{
		CIPLUSHELPER_SESSION_CREATE = 1000,
		CIPLUSHELPER_SESSION_CLOSE = 1001,
		CIPLUSHELPER_RECV_APDU = 1002,
		CIPLUSHELPER_DOACTION = 1003,
		CIPLUSHELPER_STATE_CHANGED = 1004,
		CIPLUSHELPER_DATA = 1005,
		CIPLUSHELPER_MAGIC = 987654321,
	};
};

class eDVBCIInterfaces: public eServerSocket
#else
class eDVBCIInterfaces
#endif
{
private:
	typedef enum
	{
		interface_none,
		interface_use_dvr,
		interface_use_pvr,
	} stream_interface_t;

	typedef enum
	{
		finish_none,
		finish_use_tuner_a,
		finish_use_pvr_none,
		finish_use_none,
	} stream_finish_mode_t;

	DECLARE_REF(eDVBCIInterfaces);

	stream_interface_t m_stream_interface;
	stream_finish_mode_t m_stream_finish_mode;

	static eDVBCIInterfaces *instance;
	eSmartPtrList<eDVBCISlot> m_slots;
	PMTHandlerList m_pmt_handlers; 

	eCIClient *client;
#ifndef SWIG
public:
#endif
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	eDVBCISlot *getSlot(int slotid);

	void addPMTHandler(eDVBServicePMTHandler *pmthandler);
	void removePMTHandler(eDVBServicePMTHandler *pmthandler);
	void recheckPMTHandlers();
	void gotPMT(eDVBServicePMTHandler *pmthandler);
	void ciRemoved(eDVBCISlot *slot);
	int getSlotState(int slot);

	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerText(int slot, int answer);
	int answerEnq(int slot, char *value);
	int cancelEnq(int slot);
	int getMMIState(int slot);
	int sendCAPMT(int slot);
	int setInputSource(int tunerno, const std::string &source);
	int setCIClockRate(int slot, int rate);

	void newConnection(int socket);
	void connectionLost();

#ifdef SWIG
public:
#endif
	static eDVBCIInterfaces *getInstance();
	int getNumOfSlots() { return m_slots.size(); }
	PyObject *getDescrambleRules(int slotid);
	RESULT setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject) );
	PyObject *readCICaIds(int slotid);

	void sendDataToHelper(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len);
	bool isClientConnected();
};

#endif
