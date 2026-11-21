#ifndef __esettings_h
#define __esettings_h
#include <string>

/* Settings that the Python config layer pushes into C++.
 *
 * openBH keeps its subtitle/audio options in the Python config tree and reads
 * them back through eConfigManager, so this class only carries the few values
 * that the C++ side needs at a point where the config layer is not available
 * (or where a per-service copy is required). */

class eSettings
{
public:
  eSettings() = default;

  /* RAM timeshift delay in seconds. 0 disables the in-memory buffer, so the
   * service factory keeps creating ordinary disk-backed eDVBServicePlay
   * instances. Clamped to 0..30 to keep the ring buffer size sane. */
  static void setRamTimeshift(int delay) {
      if (delay < 0)
          delay = 0;
      if (delay > 30)
          delay = 30;
      ram_timeshift_delay_seconds = delay;
  }

  static int ram_timeshift_delay_seconds;
};

#endif
