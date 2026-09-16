package institute.castalia.atlas.player.audio

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.content.ContextCompat
import kotlin.concurrent.thread
import kotlin.math.sqrt

class AudioMonitor(
    private val onLevel: (Double) -> Unit,
    private val onArousal: () -> Unit,
    private val onCalm: () -> Unit
) {

    enum class WatchFor { NONE, DARK, SOOTHE }

    @Volatile
    var watchFor = WatchFor.NONE

    @Volatile
    var running = false
        private set

    @Volatile
    var lastLevel = 0.0
        private set

    fun hasPermission(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    fun start() {
        if (running) return
        running = true
        thread(name = "atlas-mic") { loop() }
    }

    fun stop() {
        running = false
    }

    private fun loop() {
        val sampleRate = 16_000
        val minBuf = AudioRecord.getMinBufferSize(
            sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        )
        val record = AudioRecord(
            MediaRecorder.AudioSource.MIC, sampleRate,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
            minBuf * 4
        )
        record.startRecording()
        val buf = ShortArray(2048)
        val window = ArrayDeque<Double>()
        val chunkMs = 2048.0 / sampleRate * 1000.0
        var loudMs = 0.0
        var quietMs = 0.0

        while (running) {
            val n = record.read(buf, 0, buf.size)
            if (n <= 0) continue
            var acc = 0.0
            for (i in 0 until n) acc += buf[i].toDouble() * buf[i]
            val rms = sqrt(acc / n) / 32768.0
            lastLevel = rms
            onLevel(rms)
            window.addLast(rms)
            if (window.size > WINDOW) window.removeFirst()
            val avg = window.average()

            if (watchFor == WatchFor.DARK) {
                if (avg > THRESHOLD) loudMs += chunkMs else loudMs = 0.0
                if (loudMs > AROUSAL_SUSTAIN_MS) {
                    loudMs = 0.0
                    quietMs = 0.0
                    onArousal()
                }
            } else if (watchFor == WatchFor.SOOTHE) {
                if (avg < THRESHOLD) quietMs += chunkMs else quietMs = 0.0
                if (quietMs > CALM_SUSTAIN_MS) {
                    quietMs = 0.0
                    loudMs = 0.0
                    onCalm()
                }
            } else {
                loudMs = 0.0
                quietMs = 0.0
            }
            Thread.sleep(50)
        }
        record.stop()
        record.release()
    }

    companion object {
        private const val WINDOW = 12
        const val THRESHOLD = 0.035
        private const val AROUSAL_SUSTAIN_MS = 4_000.0
        private const val CALM_SUSTAIN_MS = 180_000.0
    }
}
