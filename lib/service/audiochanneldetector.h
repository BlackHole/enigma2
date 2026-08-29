#ifndef AUDIOCHANNELDETECTOR_H
#define AUDIOCHANNELDETECTOR_H

#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/dvb/idvb.h>
#include <cstdint>
#include <vector>

class iDVBDemux;
class eDVBSoftDecoder;

/*
 * eDVBAudioChannelDetector
 *
 * Detects the channel count (2.0 / 5.1 / 7.1 / ...) of the currently
 * selected DVB audio track by inspecting a bounded amount of the actual
 * elementary stream, for codecs whose frame header encodes channel
 * layout: MPEG-1 Layer II, AC3, E-AC3, and AAC (ADTS and LATM/LOAS).
 *
 * This does NOT use PMT/EIT metadata, codec-name inference (e.g.
 * assuming AC3 == 5.1), /proc, or any hardware/Broadcom-specific
 * offsets - those approaches were evaluated during development and
 * rejected as unreliable. The bit-level parsing here mirrors the
 * DVBAudioChannels.py proof of concept, ported to run in-process
 * against native demux data instead of a raw ioctl demux fd opened
 * from Python.
 *
 * Two acquisition paths, selected by the caller:
 *
 *  - start(): live DVB, local .ts/.trp playback, and StreamRelay.
 *    Reads PES for the audio PID via iDVBDemux::createPESReader(),
 *    the same mechanism already used in this codebase for subtitle,
 *    teletext, and radiotext PES (lib/dvb/subtitle.cpp,
 *    lib/dvb/teletext.cpp, lib/dvb/radiotext.cpp). The reader delivers
 *    raw bytes straight off the demux fd (PES headers included,
 *    unaligned to packet boundaries) - the byte-level sync scanners
 *    below tolerate that exactly as the Python proof of concept did.
 *
 *  - startSoftCSA(): SoftCSA. A second independent TSRecorder sharing
 *    the live eDVBCSASession was deliberately rejected: eDVBCSAEngine
 *    keeps reusable scratch buffers (m_batch_even/m_batch_odd) that
 *    are only safe for a single concurrent caller, so two recorders
 *    calling descramble() on the same session/engine at once would
 *    race. Instead this taps the *existing* SoftCSA recorder
 *    (eDVBSoftDecoder::setAudioMonitorFD) right after it descrambles
 *    in place, via a best-effort, non-blocking monitor fd - see
 *    eDVBTSRecorder::setMonitorFD. That delivers raw TS packets for
 *    every PID the recorder carries, so this path additionally filters
 *    down to our target PID's payload before handing bytes to the same
 *    byte-level scanners used everywhere else.
 *
 * In both cases the probe is bounded: it stops itself (closing the
 * reader or detaching the monitor fd) as soon as a channel count is
 * found, on timeout, or once a fixed number of bytes have been
 * inspected without a match. It never remains an active demux consumer
 * or monitor beyond that point.
 */
class eDVBAudioChannelDetector : public iObject, public sigc::trackable
{
	DECLARE_REF(eDVBAudioChannelDetector);
public:
	// Keep in sync with eDVBServicePMTHandler::program::audioStream::type
	// (lib/dvb/pmtparse.h) via codecFromStreamType(). DTS/DTS-HD/LPCM/DRA/
	// AC4 are intentionally excluded - unsupported, no probing attempted.
	enum { ctUnsupported = -1, ctMPEG, ctAC3, ctEAC3, ctAAC };

	eDVBAudioChannelDetector();
	~eDVBAudioChannelDetector();

	// True if this probe already covers the given pid/codec/source identity,
	// i.e. no need to start a new one. 'identity' distinguishes e.g. two
	// different demux instances (live vs. timeshift) using the same pid.
	bool matches(int pid, int codec, const void *identity) const;

	// Start for live DVB / local file / StreamRelay: reads PES for 'pid'
	// from 'demux'. Safe to call even if a previous probe is running; it
	// will be stopped first.
	void start(iDVBDemux *demux, int pid, int codec);

	// Start for SoftCSA: taps the post-descramble monitor fd exposed by
	// 'soft_decoder' (see eDVBSoftDecoder::setAudioMonitorFD).
	void startSoftCSA(eDVBSoftDecoder *soft_decoder, int pid, int codec);

	// Stop and release any reader/monitor fd. Safe to call repeatedly.
	void stop();

	// 0 until a channel count has actually been detected.
	int channels() const { return m_channels; }

	// Valid only once channels() > 0 and the codec is ctEAC3. True if the
	// stream carries Dolby Atmos (Joint Object Coding) metadata rather than
	// plain Dolby Digital Plus - same underlying signal (acmod/lfeon) either
	// way, so this is a separate check into the additional bitstream info,
	// not something channels() can distinguish on its own.
	bool isAtmos() const { return m_atmos; }

	// True once no further progress is possible (detected, timed out, or
	// gave up after the byte cap) - i.e. no need to keep feeding this probe.
	// For E-AC3, channels() alone isn't enough to stop: the Atmos/JOC flag
	// lives in addbsi, well past the variable-length mixing/informational
	// metadata that precedes it in the same frame - channels() can be known
	// from the first few bytes while addbsi is still out of reach. Keep
	// feeding a bit longer so isAtmos() gets a fair chance too.
	bool finished() const;

	static int codecFromStreamType(int pmt_audio_type);

	sigc::signal<void()> channelsDetected;

private:
	void reset();
	void feed(const uint8_t *data, int len);
	void tryDetect();
	void giveUp();

	void pesData(const uint8_t *data, int len);
	void monitorData(int);
	void onTimeout();

	int m_pid;
	int m_codec;
	const void *m_identity;
	bool m_softcsa;

	std::vector<uint8_t> m_data;
	int m_channels;
	bool m_atmos;
	bool m_gaveUp;

	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_pes_conn;

	int m_monitor_fd[2]; // [0] = we read (main thread), [1] = handed to the recorder to write into
	ePtr<eSocketNotifier> m_notifier;
	ePtr<eDVBSoftDecoder> m_soft_decoder; // held only to detach the monitor fd again in stop()

	ePtr<eTimer> m_timeout;
};

#endif
