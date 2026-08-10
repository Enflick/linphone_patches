/*
 * Copyright (c) 2010-2022 Belledonne Communications SARL.
 *
 * This file is part of mediastreamer2
 * (see https://gitlab.linphone.org/BC/public/mediastreamer2).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * TextNow patch: decoded downlink audio tap.
 *
 * When a process-wide callback is registered via
 * ms_set_global_decoded_audio_tap(), every AudioStream started afterwards
 * inserts a lightweight pass-through filter into its receiving graph, right
 * after the decoder (and after the generic PLC when the codec has none of
 * its own). The callback is invoked from the MSTicker thread with each
 * decoded PCM block — post packet-loss concealment, pre volume/equalizer/
 * resampler — i.e. the network-conditioned signal at the decoder output
 * rate.
 *
 * Callback contract:
 * - It runs on the real-time audio thread and MUST be non-blocking and
 *   lock-free.
 * - Each concurrently running AudioStream invokes the callback from its own
 *   ticker thread, so the callback must be thread-safe. stream_id is an
 *   opaque identity, unique and stable for the lifetime of the stream that
 *   produced the PCM — compare it, never dereference it. A consumer that
 *   only wants one stream (e.g. single-call scoring) can latch the first
 *   identity it sees and ignore the rest; identities may be reused after a
 *   stream is destroyed.
 * - Registration is not synchronized: register once, before any stream
 *   starts (e.g. before core start). Re-registering while streams are
 *   running is not supported.
 * - Register NULL to disable the tap for streams started afterwards.
 *   Clearing does NOT detach streams that are already running — they keep
 *   their copy of (cb, user_data) — so user_data must remain valid until
 *   every stream started while it was registered has been destroyed.
 */

#ifndef msdecodedaudiotap_h
#define msdecodedaudiotap_h

#include <stddef.h>
#include <stdint.h>

#include <mediastreamer2/msfilter.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*MSDecodedAudioTapCallback)(
    void *user_data, const void *stream_id, const int16_t *pcm, size_t nsamples, int sample_rate, int nchannels);

/**
 * Register (or clear, with cb=NULL) the process-wide decoded-audio tap.
 * Takes effect for streams started after the call; running streams are
 * not affected.
 */
MS2_PUBLIC void ms_set_global_decoded_audio_tap(MSDecodedAudioTapCallback cb, void *user_data);

/** Read the currently registered tap. Returns TRUE if a callback is set. */
MS2_PUBLIC bool_t ms_get_global_decoded_audio_tap(MSDecodedAudioTapCallback *cb, void **user_data);

/** Create a tap filter instance bound to the given callback (used by audiostream.c). */
MS2_PUBLIC MSFilter *ms_decoded_audio_tap_create_filter(MSFactory *factory,
                                                        MSDecodedAudioTapCallback cb,
                                                        void *user_data,
                                                        const void *stream_id,
                                                        int sample_rate,
                                                        int nchannels);

#ifdef __cplusplus
}
#endif

#endif
