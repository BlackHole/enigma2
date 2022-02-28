#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/dvb/radiotext.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/decoder.h>
#include <lib/gdi/gpixmap.h>

DEFINE_REF(eDVBRdsDecoder);

/* mode 0: RDS data is included in the audio stream
 * mode 1: RDS data is included in a separate stream/PID
 * audio_type: Used codec for audio stream. This information is needed for mode 0 as RDS data need to be extracted from the audio data
 */
eDVBRdsDecoder::eDVBRdsDecoder(iDVBDemux *demux, int mode, int audio_type)
	:msgPtr(0), bsflag(0), qdar_pos(0), t_ptr(0), qdarmvi_show(0), state(0), m_rtp_togglebit(0), m_rtp_runningbit(0)
	,m_mode(mode), m_pid(-1), m_audio_type(audio_type), m_abortTimer(eTimer::create(eApp))
{
	setStreamID(0xC0, 0xC0);

	memset(m_message_buffer, 0, sizeof(m_message_buffer));
	memset(lastmessage, 0, sizeof(lastmessage));
	memset(datamessage, 0, sizeof(datamessage));
	memset(rass_picture_mask, 0, sizeof(rass_picture_mask));
	memset(rtp_item, 0, sizeof(rtp_item));

	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create PES reader!");
	else if (mode == 0)
		m_pes_reader->connectRead(sigc::mem_fun(*this, &eDVBRdsDecoder::processData), m_read_connection);
	else
		m_pes_reader->connectRead(sigc::mem_fun(*this, &eDVBRdsDecoder::gotAncillaryData), m_read_connection);
	CONNECT(m_abortTimer->timeout, eDVBRdsDecoder::abortNonAvail);

	eTrace("[RDS] mode %d, audio_type %d", mode, audio_type);
}

eDVBRdsDecoder::~eDVBRdsDecoder()
{
	// delete cached rass slides
	for (int page=0; page < 10; ++page)
	{
		unsigned char mask = rass_picture_mask[(page*4)/8];
		if (page % 2)
			mask >>= 4;
		int subpage=0;
		while(mask)
		{
			if (mask & 1)
			{
				std::string filename = getRassPicture(page, subpage);
				if (filename.length())
					remove(filename.c_str());
			}
			mask >>= 1;
			++subpage;
		}
	}
	remove("/tmp/RassLast.mvi");
}

#define SWAP(x)	((x<<8)|(x>>8))
#define LO(x)	(x&0xFF)

static inline unsigned short crc_ccitt_byte( unsigned short crc, unsigned char c )
{
	crc = SWAP(crc) ^ c;
	crc = crc ^ (LO(crc) >> 4);
	crc = crc ^ (SWAP(LO(crc)) << 4) ^ (LO(crc) << 5);
	return crc;
}

static int bitrate[3][3][16] = {
	{
		// MPEG-2, L3
		{-1,8000,16000,24000,32000,40000,48000,56000,64000,80000,96000,112000,128000,144000,160000,0},
		// MPEG-2, L2
		{-1,8000,16000,24000,32000,40000,48000,56000,64000,80000,96000,112000,128000,144000,160000,0},
		// MPEG-2, L1
		{-1,32000,48000,56000,64000,80000,96000,112000,128000,144000,160000,176000,192000,224000,256000,0}
	},
	{
		// MPEG-1, L3
		{-1,32000,40000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000,0},
		// MPEG-1, L2
		{-1,32000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000,384000,0},
		// MPEG-1, L1
		{-1,32000,64000,96000,128000,160000,192000,224000,256000,288000,320000,352000,384000,416000,448000,0}
	},
	{
		//MPEG-2.5, L3??
		{-1,6000,8000,10000,12000,16000,20000,24000,28000,320000,40000,48000,56000,64000,80000,0},
		//MPEG-2.5, L2
		{-1,6000,8000,10000,12000,16000,20000,24000,28000,320000,40000,48000,56000,64000,80000,0},
		//MPEG-2.5, L1
		{-1,8000,12000,16000,20000,24000,32000,40000,48000,560000,64000,80000,96000,112000,128000,0}
	}
};

static int frequency[3][4] = {
	// MPEG2 - 22.05, 24, 16khz
	{ 22050,24000,16000,0 },
	// MPEG1 - 44.1, 48, 32khz
	{ 44100,48000,32000,0 },
	// MPEG2.5 - 11.025, 12, 8khz
	{ 11025,12000,8000,0 }
};

static const std::array<std::string, 256> rds_charset({
	" ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      "\n",     " ",      " ",      "\r",     " ",      " ",
	" ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      " ",      "\u00ad",
	" ",      "!",      "\"",     "#",      "\u00a4", "%",      "&",      "'",      "(",      ")",      "*",      "+",      ",",      "-",      ".",      "/",
	"0",      "1",      "2",      "3",      "4",      "5",      "6",      "7",      "8",      "9",      ":",      ";",      "<",      "=",      ">",      "?",
	"@",      "A",      "B",      "C",      "D",      "E",      "F",      "G",      "H",      "I",      "J",      "K",      "L",      "M",      "N",      "O",
	"P",      "Q",      "R",      "S",      "T",      "U",      "V",      "W",      "X",      "Y",      "Z",      "[",      "\\",     "]",      "\u2015", "_",
	"\u2016", "a",      "b",      "c",      "d",      "e",      "f",      "g",      "h",      "i",      "j",      "k",      "l",      "m",      "n",      "o",
	"p",      "q",      "r",      "s",      "t",      "u",      "v",      "w",      "x",      "y",      "z",      "{",      "|",      "}",      "\u00af", " ",
	"\u00e1", "\u00e0", "\u00e9", "\u00e8", "\u00ed", "\u00ec", "\u00f3", "\u00f2", "\u00fa", "\u00f9", "\u00d1", "\u00c7", "\u015e", "\u00df", "\u00a1", "\u0132",
	"\u00e2", "\u00e4", "\u00ea", "\u00eb", "\u00ee", "\u00ef", "\u00f4", "\u00f6", "\u00fb", "\u00fc", "\u00f1", "\u00e7", "\u015f", "\u011f", "\u0131", "\u0133",
	"\u00aa", "\u03b1", "\u00a9", "\u2030", "\u01e6", "\u011b", "\u0148", "\u0151", "\u03c0", "\u20ac", "\u00a3", "$",      "\u2190", "\u2191", "\u2192", "\u2193",
	"\u00ba", "\u00b9", "\u00b2", "\u00b3", "\u00b1", "\u0130", "\u0144", "\u0171", "\u00b5", "\u00bf", "\u00f7", "\u00b0", "\u00bc", "\u00bd", "\u00be", "\u00a7",
	"\u00c1", "\u00c0", "\u00c9", "\u00c8", "\u00cd", "\u00cc", "\u00d3", "\u00d2", "\u00da", "\u00d9", "\u0158", "\u010c", "\u0160", "\u017d", "\u0110", "\u013f",
	"\u00c2", "\u00c4", "\u00ca", "\u00cb", "\u00ce", "\u00cf", "\u00d4", "\u00d6", "\u00db", "\u00dc", "\u0159", "\u010d", "\u0161", "\u017e", "\u0111", "\u0140",
	"\u00c3", "\u00c5", "\u00c6", "\u0152", "\u0177", "\u00dd", "\u00d5", "\u00d8", "\u00de", "\u014a", "\u0154", "\u0106", "\u015a", "\u0179", "\u0166", "\u00f0",
	"\u00e3", "\u00e5", "\u00e6", "\u0153", "\u0175", "\u00fd", "\u00f5", "\u00f8", "\u00fe", "\u014b", "\u0155", "\u0107", "\u015b", "\u017a", "\u0167", " "
});

void eDVBRdsDecoder::convertRdsMessageToUTF8(unsigned char* buffer, std::string& message)
{
	int i = 0;
	message = "";
	while (buffer[i] != 0 && i < 66)
	{
		message.append(rds_charset[buffer[i]]);
		i++;
	}
}

void eDVBRdsDecoder::connectEvent(const sigc::slot<void(int)> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(slot));
}

void eDVBRdsDecoder::addToPictureMask(int id)
{
	int page = id / 1000;
	int tmp = page > 0 ? id / page : id;
	int subpage = 0;
	while(tmp > 1000)
	{
		++subpage;
		tmp -= 1000;
		tmp *= 10;
	}
	int index = (page*4+subpage)/8;
	int val = (page%2) ? 16 * (1 << subpage) : (1 << subpage);
	if (rass_picture_mask[index] & val) // already have this picture
		return;
	rass_picture_mask[index] |= val;
	/* emit */ m_event(RassInteractivePicMaskChanged);
}

void eDVBRdsDecoder::removeFromPictureMask(int id)
{
	int page = id / 1000;
	int tmp = page > 0 ? id / page : id;
	int subpage = 0;
	while(tmp > 1000)
	{
		++subpage;
		tmp -= 1000;
		tmp *= 10;
	}
	int index = (page*4)/8;
	int val = (page%2) ? 16 * (1 << subpage) : (1 << subpage);
	if (rass_picture_mask[index] & val) // have this picture
	{
		rass_picture_mask[index] &= ~val;
		/* emit */ m_event(RassInteractivePicMaskChanged);
	}
}

void eDVBRdsDecoder::processPESPacket(uint8_t *data, int len)
{
	int pos=9+data[8];// skip pes header

	if (m_audio_type == eDVBAudio::aAAC  || m_audio_type == eDVBAudio::aAACHE)
		processPESAACPacket(data, pos, len);
	else
		processPESMPEGPacket(data, pos, len);

}

void eDVBRdsDecoder::processPESAACPacket(uint8_t *data, int pos, int len)
{
	int audioMuxLength;

	while ((pos + 3) < len)
	{
		if (data[pos] == 0x56 && (data[pos + 1] & 0xE0) == 0xE0) // find 0x56E (11 bit) loas sync header
		{
			audioMuxLength = ((data[pos + 1] & 0x1F) << 8) + data[pos + 2];
			pos += 3;

			if (audioMuxLength >  (len-pos)) // length invalid -> find sync
			{
				eWarning("[RDS] Invalid aac frame");
				continue;
			}

			processAACFrame(data + pos, audioMuxLength);
			pos += audioMuxLength;
		}
		else
		{
			// eTrace("[RDS] aac stream sync lost");
			pos++;
		}
	}
}

/* RDS data is included in the DSE element of the AAC bit stream. To find this element you have to parse complete AAC frame as there are almost
 * no length fields in the data to skip unnecessary elements. To avoid writing another complex AAC parser, we try to find the DSE element
 * by parsing the frame from the end. This should work in most cases. False positives are recognized later on basis of length and CRC.
 * Format AAC frame: <other><DSE><FIL><TERM>   // DSE and FIL are optional
 * An element starts with a 3 bit element ID followed by a 4 bit instance tag (except TERM).
 * element IDs: <DSE>=4 (100), <FIL>=6 (110), <TERM>=7 (111)
 * AAC is a bitstream and is not byte-aligned!
 */
void eDVBRdsDecoder::processAACFrame(uint8_t *data, int len)
{
	int pos = len -1;
	int tmp;
	int prev_tmp;
	int skip_bits = 0;
	int count = 0;

	// skip trailing 0x00
	while (pos > 0 && data[pos] == 0x00)
		pos--;

	// search TERM in the last 2 bytes of the frame
	if ((pos - 1) < 0)
		return;
	tmp = (data[pos - 1] << 8) + data[pos];
	tmp &= 0xFF;
	while ((tmp & 0x3) != 0x3 && skip_bits < 7)
	{
		tmp >>= 1;
		skip_bits++;
	}
	if (skip_bits == 8) // TERM not found -> frame invalid -> skip it
	{
		eWarning("[RDS] Invalid aac frame without TERM");
		return;
	}

	// skip TERM
	skip_bits += 3;
	if (skip_bits >= 8)
	{
		pos--;
		skip_bits -= 8;
	}

	// search (simple/empty) FIL in the last 2 bytes of the frame
	if (pos - 1 < 0)
		return;
	tmp = (data[pos - 1] << 8) + data[pos];
	tmp >>= skip_bits;
	tmp &= 0xFF;
	if ((tmp & 0x7F) == 0x60) // FIL present?
	{
		skip_bits += 7;
		if (skip_bits >= 8)
		{
			pos--;
			skip_bits -= 8;
		}
	}

	// search DSE
	// DSE format:  id     tag     align   count     payload
	//             <100> <4 bits> <1 bit> <8 bits> <count bytes>
	prev_tmp = -1; // to store potential payload count of bytes
	while ((pos - 1) > 0 && count < 80) // search in the last 80 bytes for the DSE
	{
		prev_tmp = tmp;
		tmp = (data[pos - 1] << 8) + data[pos];
		tmp >>= skip_bits;
		tmp &= 0xFF;
		if (tmp == 0x80 && count - 1 == prev_tmp && count > 1) // 0x80 = id 100 + tag 0000 + non aligned 0 // todo aligned
		{
			uint8_t ancillaryData[count-1];
			for (int h = 1; h < count; h++)
			{
				tmp = (data[pos + h] << 8) + data[pos + h + 1];
				tmp >>= skip_bits;
				tmp &= 0xFF;
				ancillaryData[h-1] = tmp;
			}

			m_abortTimer->stop();
			gotAncillaryData(ancillaryData, count-1);
			return;
		}
		count++;
		pos--;
	}
}

void eDVBRdsDecoder::processPESMPEGPacket(uint8_t *data, int pos, int len)
{
	while (pos < len)
	{
		if ((0xFF & data[pos]) != 0xFF || (0xF0 & data[pos + 1]) != 0xF0)
			return;

		int padding_bit = (data[pos + 2]>>1) & 1;
		int mode = (data[pos + 3]>>6) & 3;
		int channel = mode == 3 ? 1 : 2;
		int id = (data[pos + 1] >> 3) & 1;
		int emphasis_bit = data[pos + 3] & 3;
		//int protection_bit = data[pos + 1] & 1;
		int rate = -1;
		int sample_freq = -1;
		int layer = -1;

		if (emphasis_bit == 2 && id == 1 )
			id = 2;

		if ((layer = (data[pos + 1]>>1) & 3) < 1)
			return;

		if ((rate = bitrate[id][layer - 1][(data[pos + 2]>>4) & 0xf]) < 1)
			return;

		if ((sample_freq = frequency[id][(data[pos + 2]>>2) & 3]) == 0)
			return;

		if (id == 1 && layer == 2)
		{
			if (rate / channel < 32000)
				return;
			if (rate / channel > 192000)
				return;
		}

		int frame_size = layer < 3 ?
			(144 * rate / sample_freq) + padding_bit :
			((12 * rate / sample_freq) * 4) + (4 * padding_bit);

		pos += frame_size;

#if 0
//		eDebug("protection_bit ? %d", protection_bit);
//		int offs = protection_bit ? pos - 1 : pos - 3;
//		if (data[offs] != 0xFD)
//			offs += 2;
//		eDebug("%02x %02x %02x %02x %02x", data[offs-2], data[offs-1], data[offs], data[offs+1], data[offs+2]);
#else
		int offs = pos - 1;
#endif

		if (data[offs] == 0xFD)
		{
			m_abortTimer->stop();
			int ancillary_len = 1 + data[offs - 1];
			offs -= ancillary_len;
			gotAncillaryData(data+offs, ancillary_len-1);
		}
	}
}

void eDVBRdsDecoder::process_qdar(unsigned char *buf)
{
	if (buf[0] == 0x40 && buf[1] == 0xDA)
	{
		unsigned int item,cnt,ctrl,item_type;
		unsigned long item_length,id,item_no,ptr,tmp;
		unsigned short crc_qdar,crc_read;
		char fname[50];
		ptr=4;cnt=0;
		item=buf[2]<<8; // Number of Items
		item|=buf[3];

		while ( cnt++ < item ) //read in items
		{
			id=buf[ptr++]<<8; //QDarID
			id|=buf[ptr++];

			item_no=buf[ptr++]<<8; // Item Number
			item_no|=buf[ptr++];

			ctrl=buf[ptr++]; //controlbyte
			item_type=buf[ptr++]; //item type

			item_length=buf[ptr++]<<24; // Item length
			item_length|=buf[ptr++]<<16;
			item_length|=buf[ptr++]<<8;
			item_length|=buf[ptr++];

			ptr=ptr+4; // rfu Bytes ... not used
			tmp=ptr; // calc crc
			crc_qdar=0xFFFF;
			while (tmp < ptr+item_length)
				crc_qdar = crc_ccitt_byte(crc_qdar, buf[tmp++]);

			crc_read=buf[ptr+item_length]<<8;
			crc_read|=buf[ptr+item_length+1];
			//eDebug("[RDS/Rass] CRC read: %04X calculated: %04X",crc_read,crc_qdar^0xFFFF);

			if (crc_read == (crc_qdar^0xFFFF)) // process item
			{
				switch(item_type)
				{
					case 0x01: //Stillframe
						if (ctrl&0x01) // display slide
						{
							sprintf(fname,"/tmp/RassLast.mvi");
							{
								CFile fh(fname,"wb");
								fwrite(buf+ptr,1,item_length-2,fh);
							}
							/*emit*/ m_event(RecvRassSlidePic);
							qdarmvi_show=1;
						}
						if (ctrl&0x02) // save slide for interactive mode
						{
							if (id == 0 || id >= 1000)
							{
								sprintf(fname,"/tmp/Rass%04d.mvi",(int)id);
								{
									CFile fh(fname,"wb");
									fwrite(buf+ptr,1,item_length-2,fh);
								}
								addToPictureMask(id);
							}
							else
								eDebug("ignore recv interactive picture id %lu", id);
						}
						if (ctrl&0x04) // display slide if nothing had been displayed yet
						{
							if (qdarmvi_show != 1)
							{
								sprintf(fname,"/tmp/RassLast.mvi");
								{
									CFile fh(fname,"wb");
									fwrite(buf+ptr,1,item_length-2,fh);
								}
								/*emit*/ m_event(RecvRassSlidePic);
								qdarmvi_show=1;
							}
						}
						if (ctrl&0x08) // delete slide
						{
							eDebug("delete slide id %lu, item_no %lu", id, item_no);
							if (id == 0 || id >= 1000)
							{
								eDebug("delete %lu", id);
								removeFromPictureMask(id);
								sprintf(fname,"/tmp/Rass%04d.mvi",(int)id); // was item_no ? ! ?
								remove(fname);
							}
							else
								eDebug("ignore del interactive picture id %lu", id);
						}
						break;
					default: //nothing more yet defined
						break;
				}
			}
			else
			{
				eDebug("[RDS/Rass] CRC error, skip Rass-Qdar-Item");
			}

			ptr=+item_length;
		}
	}
	else
	{
		eDebug("[RDS/Rass] No Rass-QDAR archive (%02X %02X) so skipping !\n",buf[0],buf[1]);
	}
}

void eDVBRdsDecoder::gotAncillaryData(const uint8_t *buf, int len)
{
	if (len <= 0)
		return;

	int pos;
	int dir;

	// RDS data included in MPEG Audio frames needs to be readed in reverse order
	if (m_mode == 1 || m_audio_type == eDVBAudio::aAAC || m_audio_type == eDVBAudio::aAACHE)
	{
		pos = 0;
		dir = 1;
	}
	else
	{
		pos = len-1;
		dir = -1;
	}

	//eTraceNoNewLineStart("[RDS] data: ");
	//for (int j = pos; j < len && j >= 0; j += dir)
	//	eTraceNoNewLine("%02x ", buf[j]);
	//eTrace("\n");

	while ( len )
	{
		unsigned char c = buf[pos];

		pos += dir;

		--len;

		if (c == 0xFF) // stop byte: force reset state
			state = 0;

		// recognize byte stuffing
		if (c == 0xFD && bsflag == 0 && state > 0)
		{
			bsflag = 1; // replace next character
			continue;
		}
		else if (bsflag == 1) // byte stuffing
		{
			bsflag = 0;
			switch (c)
			{
				case 0x00: c=0xFD; break;
				case 0x01: c=0xFE; break;
				case 0x02: c=0xFF; break;
			}
		}
		else
			bsflag = 0;

		if (bsflag == 0)
		{
			if ( state == 1 )
				crc=0xFFFF;
			if (( state >= 1 && state < 11 ) || ( state >=26 && state < 36 ) || ( state >=38 && state < 47 ))
				crc = crc_ccitt_byte(crc, c);

			switch (state)
			{
				case 0:
					if ( c==0xFE )  // start byte
						state=1;
					break;
				case 1: // 10bit Site Address + 6bit Encoder Address
				case 2:
				case 3: // Sequence Counter
					++state;
					break;
				case 4:
					leninfo=c;
					++state;
					break;
				case 5:
					switch (c)
					{
						case 0x0A: // Radiotext
							++state;
							break;
						case 0x46: // Radiotext Plus tags
							state=38;
							break;
						case 0xDA: // Rass
							state=26;
							break;
						default: // reset to state 0
							state=0;
					}
					break;

					// process Radiotext
				case 6: // Data Set Number ... ignore
				case 7: // Program Service Number ... ignore
					++state;
					break;
				case 8: // Message Element Length
					text_len=c;
					if ( !text_len || text_len > 65 || text_len > leninfo-4)
						state=0;
					else
					{
						++state;
						text_len-=2;
						msgPtr=0;
						memset(m_message_buffer, 0, sizeof(m_message_buffer));
					}
					break;
				case 9: // Radio Text Status bit:
					// 0   = AB-flagcontrol
					// 1-4 = Transmission-Number
					// 5-6 = Buffer-Config
					++state; // ignore ...
					break;
				case 10:
					m_message_buffer[msgPtr++]=c;
					if(text_len)
						--text_len;
					else
						++state;
					break;
				case 11:
					crc16=c<<8;
					++state;
					break;
				case 12:
					crc16|=c;
					m_message_buffer[msgPtr--]=0;
					while(m_message_buffer[msgPtr] == ' ' && msgPtr > 0)
						m_message_buffer[msgPtr--] = 0;
					if ( crc16 == (crc^0xFFFF) )
					{
						memcpy(lastmessage, m_message_buffer, 66);
						convertRdsMessageToUTF8(m_message_buffer, m_rt_message);
						eDebug("[RDS] radiotext str: (%s)", m_rt_message.c_str());
						/*emit*/ m_event(RadioTextChanged);
					}
					else
					{
						eDebug("[RDS] invalid radiotext crc (%s)", m_message_buffer);
						lastmessage[0] = 0; // don't use message for next radiotext plus messages as it's the old/wrong message
					}
					state=0;
					break;

				// process Rass
				case 26: //MEL
					text_len = c;
					text_len2 = c;
					++state;
					text_len-=9;
					text_len2-=9;
					t_ptr=0;
					break;
				case 27: // SID not used atm
					++state;
					break;
				case 28: // SID not used atm
					++state;
					break;
				case 29: // PNR packet number
					part=c<<16;
					++state;
					break;
				case 30: // PNR packet number
					part|=c<<8;
					++state;
					break;
				case 31: // PNR packet number
					part|=c;
					++state;
					break;
				case 32: // NOP number of packets
					parts=c<<16;
					++state;
					break;
				case 33: // NOP number of packets
					parts|=c<<8;
					++state;
					break;
				case 34: // NOP number of packets
					parts|=c;
					++state;
					break;
				case 35:
					datamessage[t_ptr++]=c;
					if(text_len)
						--text_len;
					else
						++state;
					break;
				case 36:
					crc16=c<<8;
					++state;
					break;
				case 37:
					crc16|=c;
					//eDebug("[RDS/Rass] CRC read: %04X CRC calculated: %04X",crc16,crc^0xFFFF);
					state=0;
					if ( crc16 == (crc^0xFFFF) )
					{
						if (partcnt == -1)
							partcnt=1;
						if (partcnt == part)
						{
							memcpy(qdar+qdar_pos,datamessage,text_len2+1);
							qdar_pos=qdar_pos+text_len2+1;
							if (partcnt == parts)
							{
								process_qdar(qdar); // decode qdar archive
								qdar_pos=0;
								partcnt=-1;
							}
							else
								++partcnt;
						}
						else
						{
							qdar_pos=0;
							partcnt=-1;
						}
					}
					else
					{
						eDebug("[RDS/Rass] CRC error, skip Rass-Qdar-Packet");
						eDebug("[RDS/Rass] CRC read: %04X CRC calculated: %04X",crc16,crc^0xFFFF);
						partcnt=-1;
					}
					state=0;
					break;

				// process RT plus tags ...
				case 38: // Message Element Length
					text_len=c;
					if (leninfo == 10 && text_len == 8) // RT plus message has fix size
						++state;
					else
						state = 0;
					break;
				case 39: // Application ID (2 bytes); RT+ uses 0x4BD7; ignore all other ids
					if (c != 0x4B)
						state = 0;
					else
						++state;
					break;
				case 40:
					if (c != 0xD7)
						state = 0;
					else
						++state;
					break;
				case 41: // configuration ... ignore
					++state;
					break;
				case 42:
					rtp_buf[0]=c;
					++state;
					break;
				case 43:
					rtp_buf[1]=c;
					++state;
					break;
				case 44:
					rtp_buf[2]=c;
					++state;
					break;
				case 45:
					rtp_buf[3]=c;
					++state;
					break;
				case 46:
					rtp_buf[4]=c;
					++state;
					break;
				case 47:
					crc16=c<<8;
					++state;
					break;
				case 48:
					crc16 |= c;
					if ( crc16 == (crc^0xFFFF) )
					{
						// bit 10#4 = Item Togglebit
						// bit 10#3 = Item Runningbit
						// Tag1: bit 10#2..11#5 = Contenttype, 11#4..12#7 = Startmarker, 12#6..12#1 = Length
						if (lastmessage[0] == 0) // radiotext message is needed as radiotext plus uses this data to extract strings from it
						{
							state = 0;
							break;
						}
						short current_tooglebit = rtp_buf[0]>>4;
						short current_runningbit = (rtp_buf[0]>>3) & 0x1;
						if ( current_tooglebit != m_rtp_togglebit  // current togglebit different than last stored togglebit -> item/song has changed
							|| (m_rtp_runningbit == 1 && current_runningbit == 0)) // item/song has ended
						{
							memset(rtp_item, 0, sizeof(rtp_item));
							m_rtplus_message = "";
							/*emit*/ m_event(RtpTextChanged);
						}
						m_rtp_togglebit = current_tooglebit;
						m_rtp_runningbit = current_runningbit;

						int rtp_typ[2],rtp_start[2],rtp_len[2];
						rtp_typ[0]   = (0x38 & rtp_buf[0]<<3) | rtp_buf[1]>>5;
						rtp_start[0] = (0x3e & rtp_buf[1]<<1) | rtp_buf[2]>>7;
						rtp_len[0]   = 0x3f & rtp_buf[2]>>1;
						// Tag2: bit 12#0..13#3 = Contenttype, 13#2..14#5 = Startmarker, 14#4..14#0 = Length(5bit)
						rtp_typ[1]   = (0x20 & rtp_buf[2]<<5) | rtp_buf[3]>>3;
						rtp_start[1] = (0x38 & rtp_buf[3]<<3) | rtp_buf[4]>>5;
						rtp_len[1]   = 0x1f & rtp_buf[4];

						unsigned char rtplus_osd_tmp[64];
						memset(rtplus_osd_tmp, 0, sizeof(rtplus_osd_tmp));

						if (rtp_start[0] < 66 && (rtp_len[0]+rtp_start[0]) < 66)
						{
							memcpy(rtp_item[rtp_typ[0]],lastmessage+rtp_start[0],rtp_len[0]+1);
							rtp_item[rtp_typ[0]][rtp_len[0]+1]=0;
						}

						if (rtp_typ[0] != rtp_typ[1])
						{
							if (rtp_start[1] < 66 && (rtp_len[1]+rtp_start[1]) < 66)
							{
								memcpy(rtp_item[rtp_typ[1]],lastmessage+rtp_start[1],rtp_len[1]+1);
								rtp_item[rtp_typ[1]][rtp_len[1]+1]=0;
							}
						}

						// main RTPlus item_types used by the radio stations:
						// 1 title
						// 4 artist
						// 24 info.date_time
						// 31 stationname
						// 32 program.now
						// 39 homepage
						// 41 phone.hotline
						// 46 email.hotline
						// todo: make a window to display all saved items ...

						//create RTPlus OSD for title/artist
						memset(rtplus_osd, 0, sizeof(rtplus_osd));

						if ( rtp_item[4][0] != 0 && (rtp_item[4][1] != 0 || rtp_item[4][0] != 0x20))//artist
							sprintf((char*)rtplus_osd_tmp," (%.60s)",rtp_item[4]);

						if ( rtp_item[1][0] != 0 )//title
							sprintf((char*)rtplus_osd,"%s%s",rtp_item[1],rtplus_osd_tmp);

						if ( rtplus_osd[0] != 0 )
						{
							convertRdsMessageToUTF8(rtplus_osd, m_rtplus_message);
							/*emit*/ m_event(RtpTextChanged);
							eDebug("[RDS] RTPlus: %s",m_rtplus_message.c_str());
						}
					}
					else
					{
						eDebug("[RDS] RT+ invalid CRC read: %04X CRC calculated: %04X", crc16, crc^0xFFFF);
					}
					state=0;
					break;
			}
		}
	}
}

std::string eDVBRdsDecoder::getRassPicture(int page, int subpage)
{
	int val=0;

	switch(subpage)
	{
		case 0:
			val=page*1000;
			break;
		case 1:
			val=page*1100;
			break;
		case 2:
			val=page*1110;
			break;
		case 3:
			val=page*1111;
			break;
	}
	char fname[50];
	sprintf(fname,"/tmp/Rass%04d.mvi",val);
	return fname;
}

int eDVBRdsDecoder::start(int pid)
{
	int ret = -1;
	if (m_pes_reader && !(ret = m_pes_reader->start(pid)) && m_mode == 0)
		m_abortTimer->startLongTimer(20);
	m_pid = pid;
	return ret;
}

void eDVBRdsDecoder::abortNonAvail()
{
	eDebug("[RDS] no ancillary data in audio stream... abort radiotext pes parser");
	if (m_pes_reader)
		m_pes_reader->stop();
}

ePyObject eDVBRdsDecoder::getRassPictureMask()
{
	ePyObject ret = PyTuple_New(5);
	PyTuple_SET_ITEM(ret, 0, PyLong_FromLong(rass_picture_mask[0]));
	PyTuple_SET_ITEM(ret, 1, PyLong_FromLong(rass_picture_mask[1]));
	PyTuple_SET_ITEM(ret, 2, PyLong_FromLong(rass_picture_mask[2]));
	PyTuple_SET_ITEM(ret, 3, PyLong_FromLong(rass_picture_mask[3]));
	PyTuple_SET_ITEM(ret, 4, PyLong_FromLong(rass_picture_mask[4]));
	return ret;
}
