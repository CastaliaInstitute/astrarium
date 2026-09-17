package institute.castalia.atlas.player.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import kotlin.concurrent.thread
import kotlin.math.sin
import kotlin.math.sqrt

object MicTest {

    private class Probe(val source: Int, val label: String)

    private val SOURCES = listOf(
        Probe(MediaRecorder.AudioSource.MIC, "mic"),
        Probe(MediaRecorder.AudioSource.VOICE_RECOGNITION, "voice-recognition"),
        Probe(MediaRecorder.AudioSource.CAMCORDER, "camcorder"),
        Probe(MediaRecorder.AudioSource.UNPROCESSED, "unprocessed"),
        Probe(MediaRecorder.AudioSource.VOICE_COMMUNICATION, "voice-communication")
    )

    fun scan(ctx: Context): org.json.JSONObject {
        val mgr = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val inputs = mgr.getDevices(AudioManager.GET_DEVICES_INPUTS)
            .filter { it.type != AudioDeviceInfo.TYPE_REMOTE_SUBMIX }
        val devices = org.json.JSONArray()
        inputs.forEach { devices.put(org.json.JSONObject().put("type", typeName(it.type)).put("id", it.id)) }

        val results = org.json.JSONArray()
        for (probe in SOURCES) {
            val r = beepTest(probe.source)
            val st = statTest(probe.source)
            results.put(
                org.json.JSONObject()
                    .put("source", probe.label)
                    .put("ok", r.getBoolean("ok"))
                    .put("peak", r.getDouble("peak"))
                    .put("quiet", r.getDouble("quiet"))
                    .put("ratio", r.getDouble("ratio"))
                    .put("bytes", r.optInt("bytes", 0))
                    .put("playing", r.optBoolean("playing", false))
                    .put("err", r.optString("err", ""))
                    .put("noiseMin", st.getDouble("min"))
                    .put("noiseMax", st.getDouble("max"))
                    .put("noiseStd", st.getDouble("std"))
            )
        }
        inputs.firstOrNull { it.type == AudioDeviceInfo.TYPE_LINE_ANALOG }?.let { line ->
            val r = beepPinned(line)
            results.put(
                org.json.JSONObject()
                    .put("source", "line-analog (pinned)")
                    .put("ok", r.getBoolean("ok"))
                    .put("peak", r.getDouble("peak"))
                    .put("quiet", r.getDouble("quiet"))
                    .put("ratio", r.getDouble("ratio"))
                    .put("bytes", r.optInt("bytes", 0))
                    .put("playing", r.optBoolean("playing", false))
                    .put("err", r.optString("err", ""))
            )
        }
        return org.json.JSONObject().put("devices", devices).put("results", results)
    }

    private fun buildTrack(): AudioTrack? = try {
        AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(44_100)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setTransferMode(AudioTrack.MODE_STREAM)
            .setBufferSizeInBytes(44_100 * 2)
            .build()
    } catch (e: Exception) {
        null
    }

    private fun beepTest(source: Int): org.json.JSONObject {
        val sr = 16_000
        val min = AudioRecord.getMinBufferSize(sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (min <= 0) return org.json.JSONObject().put("ok", false).put("err", "no min buffer")
        val rec = try {
            AudioRecord(source, sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 2)
        } catch (e: Exception) {
            return org.json.JSONObject().put("ok", false).put("err", "build: ${e.message}")
        }
        return measure(rec, buildTrack())
    }

    private fun beepPinned(dev: AudioDeviceInfo): org.json.JSONObject {
        val sr = 16_000
        val min = AudioRecord.getMinBufferSize(sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (min <= 0) return org.json.JSONObject().put("ok", false).put("err", "no min buffer")
        val rec = try {
            AudioRecord(MediaRecorder.AudioSource.MIC, sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 2)
        } catch (e: Exception) {
            return org.json.JSONObject().put("ok", false).put("err", "build: ${e.message}")
        }
        try {
            rec.setPreferredDevice(dev)
        } catch (e: Exception) {
            return org.json.JSONObject().put("ok", false).put("err", "setPreferredDevice: ${e.message}")
        }
        return measure(rec, buildTrack())
    }

    private fun measure(rec: AudioRecord, track: AudioTrack?): org.json.JSONObject {
        if (track == null) {
            runCatching { rec.release() }
            return org.json.JSONObject().put("ok", false).put("err", "no track")
        }
        val outSr = 44_100
        val tone = ShortArray(outSr) {
            val t = 2.0 * Math.PI * it / outSr
            val s = 0.6 * sin(1200.0 * t) + 0.4 * sin(2400.0 * t)
            (22000 * s).toInt().toShort()
        }
        var bytes = 0
        var playing = false
        try {
            rec.startRecording()
            track.setVolume(1.0f)
            track.play()
            thread {
                var i = 0
                while (i * 4096 < tone.size && track.playState == AudioTrack.PLAYSTATE_PLAYING) {
                    val w = track.write(tone, i * 4096, minOf(4096, tone.size - i * 4096))
                    bytes += w
                    i++
                }
                playing = track.playState == AudioTrack.PLAYSTATE_PLAYING
            }
            val buf = ShortArray(2048)
            val t0 = System.currentTimeMillis()
            var peak = 0.0
            var quietAcc = 0.0
            var nDuring = 0
            var nQuiet = 0
            while (System.currentTimeMillis() - t0 < 2_200) {
                val n = rec.read(buf, 0, buf.size)
                if (n <= 0) continue
                var acc = 0.0
                for (i in 0 until n) acc += buf[i].toDouble() * buf[i]
                val rms = sqrt(acc / n) / 32768.0
                val at = System.currentTimeMillis() - t0
                when {
                    at in 500 until 1_600 -> { peak = maxOf(peak, rms); nDuring++ }
                    at >= 1_600 -> { quietAcc += rms; nQuiet++ }
                }
            }
            val quiet = if (nQuiet > 0) quietAcc / nQuiet else 0.0
            if (nDuring == 0) return org.json.JSONObject().put("ok", false).put("err", "no frames").put("bytes", bytes).put("playing", playing)
            return org.json.JSONObject()
                .put("ok", true)
                .put("peak", peak)
                .put("quiet", quiet)
                .put("ratio", if (quiet > 0) peak / quiet else 0.0)
                .put("bytes", bytes)
                .put("playing", playing)
        } catch (e: Exception) {
            return org.json.JSONObject().put("ok", false).put("err", e.toString()).put("bytes", bytes).put("playing", playing)
        } finally {
            runCatching { rec.stop() }
            runCatching { rec.release() }
            runCatching { track.stop() }
            runCatching { track.release() }
        }
    }

    private fun statTest(source: Int): org.json.JSONObject {
        val sr = 16_000
        val min = AudioRecord.getMinBufferSize(sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (min <= 0) return org.json.JSONObject().put("min", 0.0).put("max", 0.0).put("std", 0.0)
        val rec = try {
            AudioRecord(source, sr, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 2)
        } catch (e: Exception) {
            return org.json.JSONObject().put("min", 0.0).put("max", 0.0).put("std", 0.0)
        }
        try {
            rec.startRecording()
            val buf = ShortArray(2048)
            val t0 = System.currentTimeMillis()
            var lo = 1.0
            var hi = 0.0
            var sum = 0.0
            var n = 0
            while (System.currentTimeMillis() - t0 < 2_500) {
                val got = rec.read(buf, 0, buf.size)
                if (got <= 0) continue
                var acc = 0.0
                for (i in 0 until got) acc += buf[i].toDouble() * buf[i]
                val rms = sqrt(acc / got) / 32768.0
                lo = minOf(lo, rms); hi = maxOf(hi, rms); sum += rms; n++
            }
            return org.json.JSONObject()
                .put("min", lo).put("max", hi).put("std", if (n > 0) hi - lo else 0.0)
        } catch (e: Exception) {
            return org.json.JSONObject().put("min", 0.0).put("max", 0.0).put("std", 0.0)
        } finally {
            runCatching { rec.stop() }
            runCatching { rec.release() }
        }
    }

    private fun typeName(type: Int): String = when (type) {
        AudioDeviceInfo.TYPE_BUILTIN_MIC -> "builtin-mic"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "wired-headset"
        AudioDeviceInfo.TYPE_USB_DEVICE -> "usb"
        AudioDeviceInfo.TYPE_USB_ACCESSORY -> "usb-accessory"
        AudioDeviceInfo.TYPE_LINE_ANALOG -> "line-analog"
        AudioDeviceInfo.TYPE_LINE_DIGITAL -> "line-digital"
        AudioDeviceInfo.TYPE_HDMI -> "hdmi"
        AudioDeviceInfo.TYPE_TV_TUNER -> "tvtuner"
        AudioDeviceInfo.TYPE_FM_TUNER -> "fmtuner"
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "bt-sco"
        AudioDeviceInfo.TYPE_AUX_LINE -> "aux-line"
        else -> "type-$type"
    }
}