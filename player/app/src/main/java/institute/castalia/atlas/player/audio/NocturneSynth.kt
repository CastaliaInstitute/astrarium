package institute.castalia.atlas.player.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlin.concurrent.thread
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin
import kotlin.math.tanh
import kotlin.random.Random

class NocturneSynth {

    @Volatile
    var volume = 0f

    @Volatile
    private var pluckRequest = -1

    fun pluck(step: Int) {
        pluckRequest = step
    }

    @Volatile
    private var running = false
    private var thread: Thread? = null

    private val padPhase = DoubleArray(PAD_FREQS.size)
    private val lfoPhase = DoubleArray(LFO_FREQS.size)
    private var wanderPhase = 0.0
    private var noiseLp = 0.0
    private var nextPluck = 1.5
    private var pluckFreq = 440.0
    private var pluckAmp = 0.0
    private var pluckPhase = 0.0

    fun start() {
        if (running) return
        running = true
        thread(name = "atlas-nocturne") {
            val fmt = AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                .setSampleRate(SAMPLE_RATE)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build()
            val at = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setAudioFormat(fmt)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setBufferSizeInBytes(SAMPLE_RATE * 4)
                .build()
            at.play()
            val buf = FloatArray(BLOCK)
            val dt = 1.0 / SAMPLE_RATE
            while (running) {
                for (i in 0 until BLOCK) {
                    var s = 0.0
                    for (v in padPhase.indices) {
                        padPhase[v] += 2 * PI * PAD_FREQS[v] * dt
                        lfoPhase[v] += 2 * PI * LFO_FREQS[v] * dt
                        s += sin(padPhase[v]) * (0.5 + 0.5 * sin(lfoPhase[v])) * PAD_GAIN
                    }
                    nextPluck -= dt
                    if (nextPluck <= 0) {
                        pluckFreq = PENTATONIC[Random.nextInt(PENTATONIC.size)]
                        pluckAmp = PLUCK_GAIN
                        nextPluck = 2.0 + Random.nextDouble() * 5.0
                    }
                    if (pluckRequest >= 0) {
                        pluckFreq = PENTATONIC[pluckRequest % PENTATONIC.size]
                        pluckAmp = PLUCK_GAIN * 2.2
                        pluckPhase = 0.0
                        pluckRequest = -1
                    }
                    if (pluckAmp > 0.0001) {
                        pluckPhase += 2 * PI * pluckFreq * dt
                        s += (sin(pluckPhase) + 0.35 * sin(2 * pluckPhase)) * pluckAmp
                        pluckAmp *= exp(-dt / DECAY_TAU)
                    }
                    wanderPhase += 2 * PI * WANDER_FREQ * dt
                    val n = Random.nextDouble() * 2 - 1
                    noiseLp += NOISE_ALPHA * (n - noiseLp)
                    s += noiseLp * NOISE_GAIN * (0.6 + 0.4 * sin(wanderPhase))
                    buf[i] = tanh(s * volume).toFloat()
                }
                at.write(buf, 0, BLOCK, AudioTrack.WRITE_BLOCKING)
            }
            at.stop()
            at.release()
        }
    }

    fun stop() {
        running = false
        thread = null
    }

    companion object {
        const val SAMPLE_RATE = 44100
        private const val BLOCK = 4096
        private val PAD_FREQS = doubleArrayOf(110.0, 164.81, 220.0, 329.63)
        private val LFO_FREQS = doubleArrayOf(0.031, 0.017, 0.043, 0.026)
        private const val PAD_GAIN = 0.16
        private val PENTATONIC = doubleArrayOf(
            220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25, 587.33
        )
        private const val PLUCK_GAIN = 0.22
        private const val DECAY_TAU = 1.1
        private const val NOISE_ALPHA = 0.002
        private const val NOISE_GAIN = 0.35
        private const val WANDER_FREQ = 0.008
    }
}
