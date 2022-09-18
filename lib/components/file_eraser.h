#ifndef __lib_components_file_eraser_h
#define __lib_components_file_eraser_h

#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/base/ebase.h>

class eBackgroundFileEraser: public eMainloop, private eThread, public sigc::trackable
{
	struct Message
	{
		std::string filename;
		Message()
		{}
		Message(const std::string& afilename)
			:filename(afilename)
		{}
	};
	eFixedMessagePump<Message> messages;
	static eBackgroundFileEraser *instance;
	void gotMessage(const Message &message);
	void thread();
	void idle();
	ePtr<eTimer> stop_thread_timer;
#ifndef SWIG
public:
#endif
	eBackgroundFileEraser();
	~eBackgroundFileEraser();
#ifdef SWIG
public:
%typemap(in) (const char* filename2) {
	if (PyBytes_Check($input)) {
		$1 = PyBytes_AsString($input);
	} else {
		$1 = PyBytes_AsString(PyUnicode_AsEncodedString($input, "utf-8", "surrogateescape"));
	}
}
#endif
	void erase(const std::string& filename);
	void erase(const char* filename2);
	static eBackgroundFileEraser *getInstance() { return instance; }
	static const int ERASE_FLAG_HDD = 1;
	static const int ERASE_FLAG_OTHER = 2;
};

#endif
