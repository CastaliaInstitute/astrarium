package institute.castalia.atlas.player.sleep

import android.animation.ValueAnimator
import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.media.AudioManager
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.Window
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import institute.castalia.atlas.player.Settings
import institute.castalia.atlas.player.audio.NocturneSynth
import institute.castalia.atlas.player.data.AppDatabase
import institute.castalia.atlas.player.sky.SkyMath
import institute.castalia.atlas.player.sky.SkyTour
import institute.castalia.atlas.player.sky.SkyView
import institute.castalia.atlas.player.sky.StarField3D
import java.util.Calendar
import kotlin.concurrent.thread

class SleepGuide(
    private val activity: Activity,
    private val window: Window,
    private val overlay: View,
    private val skyView: SkyView,
    private val starField: StarField3D,
    private val db: AppDatabase,
    private val player: Player,
    private val onPhase: (Phase) -> Unit
) {

    enum class Phase { IDLE, LESSONS, MUSIC, JOURNEY, FADE, DARK, SOOTHE }

    private val handler = Handler(Looper.getMainLooper())
    private val nocturne = NocturneSynth()
    private var tour: SkyTour? = null
    private var debugMode = false
    private var pending: Runnable? = null
    private var dimRunnable: Runnable? = null
    private var dimStep = 0

    var phase = Phase.IDLE
        private set

    init {
        window.attributes = window.attributes.apply { screenBrightness = 0.01f }
    }

    private val clockWatch = object : Runnable {
        override fun run() {
            if (phase == Phase.IDLE) {
                when {
                    inNightResumeWindow() -> transition(Phase.JOURNEY)
                    inWindDownWindow() -> start()
                }
            }
            handler.postDelayed(this, 30_000L)
        }
    }

    fun beginClockWatch() {
        handler.post(clockWatch)
    }

    fun inWindDownWindow(): Boolean {
        val minute = Calendar.getInstance().let {
            it.get(Calendar.HOUR_OF_DAY) * 60 + it.get(Calendar.MINUTE)
        }
        val start = Settings.bedtimeMinutes(activity)
        val end = start + Settings.lessonWindowMinutes(activity) +
            Settings.musicMinutes(activity) + Settings.fadeMinutes(activity)
        return minute in start until end
    }

    // reboot-resume: if we come up in the middle of the night, re-enter the journey
    // (a pure function of wall clock, so position continuity holds automatically).
    // The night's journey occupies [prev-day bedtime+lessonWindow, next dawn).
    fun inNightResumeWindow(): Boolean {
        val now = System.currentTimeMillis()
        val dawn = SkyMath.nextDawnMs(
            Calendar.getInstance(),
            Settings.skyLat(activity).toDouble(),
            Settings.skyLon(activity).toDouble()
        )
        val dawnCal = Calendar.getInstance().apply { timeInMillis = dawn }
        val bedCal = Calendar.getInstance().apply {
            set(dawnCal.get(Calendar.YEAR), dawnCal.get(Calendar.MONTH), dawnCal.get(Calendar.DAY_OF_MONTH), 0, 0, 0)
            set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_MONTH, -1)
            add(Calendar.MINUTE, Settings.bedtimeMinutes(activity))
        }
        val winEnd = bedCal.timeInMillis + Settings.lessonWindowMinutes(activity) * 60_000L
        return now in winEnd until dawn
    }

    fun start() {
        debugMode = false
        handler.post { transition(Phase.LESSONS) }
    }

    fun skyNow() {
        debugMode = false
        handler.post { transition(Phase.MUSIC) }
    }

    fun debugSky(name: String?, stage: Int) {
        debugMode = true
        handler.post {
            if (phase != Phase.MUSIC) transition(Phase.MUSIC)
            tour?.stop()
            tour = null
            restoreScreen(0.85f)
            skyView.post {
                skyView.setTour(name, stage)
                if (name == null) skyView.resetCamera()
            }
        }
    }

    fun debugSkyJson(): org.json.JSONObject = skyView.debugJson()

    fun setAlign(mode: String, windows: List<institute.castalia.atlas.player.sky.StarField3D.SkyWindow>) {
        starField.setAlign(mode, windows)
    }

    fun setAlignPattern(on: Boolean) {
        starField.setPattern(on)
    }

    fun setDebugAtDest(on: Boolean) {
        starField.debugAtDest = on
    }

    fun setTimeScale(scale: Float) {
        starField.setTimeScale(scale)
    }

    fun alignState(): org.json.JSONObject = starField.alignJson()

    fun applyLiveSettings() {
        if (phase == Phase.LESSONS || phase == Phase.MUSIC) restoreScreen()
    }

    fun setConsLines(on: Boolean) {
        Settings.setConstellationLines(activity, on)
        starField.setConsLines(on)
    }

    fun setConsArt(on: Boolean) {
        Settings.setConstellationArt(activity, on)
        starField.setConsArt(on)
    }

    fun consState(): org.json.JSONObject = org.json.JSONObject()
        .put("lines", starField.showLines)
        .put("art", starField.showArt)

    fun lookAtStar(name: String): Boolean = starField.lookAtStar(name)

    fun lookAtCons(name: String): Boolean = starField.lookAtCons(name)

    fun clearLook() = starField.clearLook()

    fun setLookOffset(yawDeg: Double, pitchDeg: Double) = starField.setLookOffset(yawDeg, pitchDeg)

    fun skyObjects(): org.json.JSONObject = starField.skyObjects()

    fun wake() {
        handler.post {
            cancelSlowDim()
            restoreScreen()
            if (phase == Phase.DARK) {
                phase = Phase.IDLE
                onPhase(phase)
            }
        }
    }

    fun onArousal() {
        if (!Settings.monitorEnabled(activity)) return
        if (phase == Phase.DARK) handler.post { transition(Phase.SOOTHE) }
    }

    fun onCalm() {
        if (phase == Phase.SOOTHE) handler.post { transition(Phase.FADE) }
    }

    private fun ensureVolume() {
        val am = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val target = (max * Settings.speakerVolume(activity) / 20f).toInt().coerceIn(1, max)
        am.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0)
    }

    private fun transition(next: Phase) {
        pending?.let { handler.removeCallbacks(it) }
        phase = next
        onPhase(next)
        when (next) {
            Phase.LESSONS -> {
                restoreScreen()
                nocturne.stop()
                tour?.stop()
                ensureVolume()
                starField.start(lessonWindowEnd())
                val musicAt = (lessonWindowEnd() - Settings.musicMinutes(activity) * 60_000L)
                    .coerceAtLeast(System.currentTimeMillis() + 60_000L)
                schedule(Phase.MUSIC, musicAt - System.currentTimeMillis())
            }
            Phase.MUSIC -> {
                ensureVolume()
                beginMusic()
                val lessonEnd = lessonWindowEnd()
                val toJourney = (lessonEnd - System.currentTimeMillis()).coerceAtLeast(30_000L)
                schedule(Phase.JOURNEY, toJourney)
            }
            Phase.JOURNEY -> {
                tour?.stop()
                player.stop()
                player.clearMediaItems()
                restoreScreen()
                beginJourney()
                val dawn = SkyMath.nextDawnMs(
                    Calendar.getInstance(),
                    Settings.skyLat(activity).toDouble(),
                    Settings.skyLon(activity).toDouble()
                )
                schedule(Phase.FADE, (dawn - System.currentTimeMillis()).coerceIn(60_000L, 12 * 3600_000L))
            }
            Phase.FADE -> {
                tour?.stop()
                fadeToBlack(Settings.fadeMinutes(activity) * 60_000L)
                schedule(Phase.DARK, Settings.fadeMinutes(activity) * 60_000L)
            }
            Phase.DARK -> {
                tour?.stop()
                starField.stop()
                player.stop()
                player.clearMediaItems()
                fadeOutAudio(15_000L)
                darken()
                startSlowDim()
            }
            Phase.SOOTHE -> {
                tour?.stop()
                starField.stop()
                restoreScreen(Settings.sootheBrightness(activity))
                beginSoothe()
            }
            Phase.IDLE -> {
                restoreScreen()
                nocturne.stop()
                tour?.stop()
                player.stop()
                player.clearMediaItems()
                starField.stop()
            }
        }
    }

    private fun beginMusic() {
        if (Settings.skyMode(activity) == "journey") {
            if (Settings.nocturneEnabled(activity)) {
                nocturne.start()
                rampVolume(0.4f, 5_000L)
            }
            beginJourney()
            playJourneyNarration()
        } else if (Settings.skyDuringMusic(activity)) {
            if (Settings.nocturneEnabled(activity)) {
                nocturne.start()
                rampVolume(0.45f, 5_000L)
            }
            tour?.stop()
            tour = if (debugMode) null else SkyTour(db, player, skyView, nocturne, Settings.activeBand(activity)) { }
            tour?.start()
        } else if (Settings.nocturneEnabled(activity)) {
            nocturne.start()
            rampVolume(0.5f, 5_000L)
        } else {
            playSleepMusic(0.5f)
        }
    }

    private fun beginJourney() {
        val cal = Calendar.getInstance()
        val lat = Settings.skyLat(activity).toDouble()
        val lon = Settings.skyLon(activity).toDouble()
        val dawn = SkyMath.nextDawnMs(cal, lat, lon)
        val dawnCal = Calendar.getInstance().apply { timeInMillis = dawn }
        val midnight = Calendar.getInstance().apply {
            set(dawnCal.get(Calendar.YEAR), dawnCal.get(Calendar.MONTH), dawnCal.get(Calendar.DAY_OF_MONTH), 0, 0, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
        val bed = Calendar.getInstance().apply {
            set(dawnCal.get(Calendar.YEAR), dawnCal.get(Calendar.MONTH), dawnCal.get(Calendar.DAY_OF_MONTH), 0, 0, 0)
            set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_MONTH, -1)
            add(Calendar.MINUTE, Settings.bedtimeMinutes(activity))
        }
        val outboundStart = bed.timeInMillis + Settings.lessonWindowMinutes(activity) * 60_000L
        thread {
            val featured = featuredConstellation()
            val figStars = featured?.let { skyView.figStarCoords(it) }?.ifEmpty { null }
            handler.post {
                android.util.Log.d(
                    "SleepGuide",
                    "beginJourney featured=$featured figStars=${figStars?.size ?: 0}"
                )
                starField.start(dawn, midnight, outboundStart, featured, figStars)
            }
        }
    }

    private fun lessonWindowEnd(): Long {
        val bed = Settings.bedtimeMinutes(activity)
        val cal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, bed / 60)
            set(Calendar.MINUTE, bed % 60)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        if (cal.timeInMillis > System.currentTimeMillis()) cal.add(Calendar.DAY_OF_MONTH, -1)
        return cal.timeInMillis + Settings.lessonWindowMinutes(activity) * 60_000L
    }

    private var courseOverride: String? = null

    fun setCourse(name: String?) {
        courseOverride = name
    }

    fun telemetryJson(): org.json.JSONObject = starField.telemetryJson()
        .put("phase", phase.name)
        .put("course", courseOverride)

    private fun featuredConstellation(): String? {
        courseOverride?.let { return it }
        return try {
            db.lessons().all()
                .filter { it.subject == "sky" && it.band == Settings.activeBand(activity) }
                .sortedBy { it.durationSec }
                .firstNotNullOfOrNull { institute.castalia.atlas.player.sky.SkyTour.constellationsFor(it.title).firstOrNull() }
        } catch (e: Exception) {
            null
        }
    }

    private fun playJourneyNarration() {
        val nowMin = Calendar.getInstance().let {
            it.get(Calendar.HOUR_OF_DAY) * 60 + it.get(Calendar.MINUTE)
        }
        if (!Settings.lessonWindowOpen(activity, nowMin)) return
        thread {
            val lesson = db.lessons().all()
                .filter { it.subject == "journey" && it.band == Settings.activeBand(activity) }
                .minByOrNull { it.durationSec }
            handler.post {
                if (lesson != null) {
                    player.setMediaItem(MediaItem.fromUri(lesson.filePath))
                    player.prepare()
                    player.volume = 0.55f
                    player.play()
                }
            }
        }
    }

    private fun beginSoothe() {
        if (Settings.nocturneEnabled(activity)) {
            nocturne.start()
            rampVolume(0.26f, 3_000L)
        } else {
            playSleepMusic(0.26f)
        }
    }

    private fun rampVolume(target: Float, durationMs: Long) {
        val animator = ValueAnimator.ofFloat(nocturne.volume, target)
        animator.duration = durationMs
        animator.addUpdateListener { nocturne.volume = it.animatedValue as Float }
        animator.start()
    }

    private fun fadeOutAudio(durationMs: Long) {
        val animator = ValueAnimator.ofFloat(nocturne.volume, 0f)
        animator.duration = durationMs
        animator.addUpdateListener { nocturne.volume = it.animatedValue as Float }
        animator.start()
        handler.postDelayed({ nocturne.stop() }, durationMs + 1_000L)
    }

    private fun schedule(next: Phase, delayMs: Long) {
        val run = Runnable { transition(next) }
        pending = run
        handler.postDelayed(run, delayMs)
    }

    private fun playLessonQueue() {
        thread {
            val items = db.queue().all()
                .mapNotNull { db.lessons().byId(it.lessonId) }
            handler.post {
                if (items.isEmpty()) {
                    transition(Phase.MUSIC)
                } else {
                    player.setMediaItems(items.map { MediaItem.fromUri(it.filePath) })
                    player.repeatMode = Player.REPEAT_MODE_OFF
                    player.prepare()
                    player.volume = 0.8f
                    player.play()
                }
            }
        }
    }

    private fun playSleepMusic(volume: Float) {
        thread {
            val music = db.lessons().sleepMusic()
            handler.post {
                if (music != null) {
                    player.setMediaItem(MediaItem.fromUri(music.filePath))
                    player.prepare()
                    player.volume = volume
                    player.play()
                }
            }
        }
    }

    private fun restoreScreen(brightness: Float = Settings.nightBrightness(activity)) {
        window.attributes = window.attributes.apply { screenBrightness = brightness }
        overlay.background = ColorDrawable(Color.argb(Settings.amberAlpha(activity), 242, 178, 92))
    }

    private fun fadeToBlack(durationMs: Long) {
        val from = window.attributes.screenBrightness
        val startColor = (overlay.background as? ColorDrawable)?.color
            ?: Color.argb(Settings.amberAlpha(activity), 242, 178, 92)
        val startVolume = nocturne.volume
        val animator = ValueAnimator.ofFloat(0f, 1f)
        animator.duration = durationMs
        animator.addUpdateListener {
            val f = it.animatedFraction
            window.attributes = window.attributes.apply {
                screenBrightness = from + (0.01f - from) * f
            }
            overlay.background = ColorDrawable(
                Color.argb(
                    (Color.alpha(startColor) + (255 - Color.alpha(startColor)) * f).toInt(),
                    (Color.red(startColor) * (1f - f)).toInt(),
                    (Color.green(startColor) * (1f - f)).toInt(),
                    (Color.blue(startColor) * (1f - f)).toInt()
                )
            )
            if (Settings.nocturneEnabled(activity)) {
                nocturne.volume = startVolume * (1f - f)
            }
        }
        animator.start()
    }

    private fun darken() {
        window.attributes = window.attributes.apply { screenBrightness = 0.01f }
        overlay.background = ColorDrawable(Color.BLACK)
    }

    private fun startSlowDim() {
        cancelSlowDim()
        dimStep = 0
        val steps = floatArrayOf(0.01f, 0.008f, 0.006f, 0.004f, 0.003f, 0.002f, 0.001f, 0.0005f, 0f)
        dimRunnable = object : Runnable {
            override fun run() {
                if (phase != Phase.DARK) return
                if (dimStep < steps.size) {
                    window.attributes = window.attributes.apply { screenBrightness = steps[dimStep] }
                    dimStep++
                    handler.postDelayed(this, 60_000L)
                }
            }
        }
        handler.postDelayed(dimRunnable!!, 60_000L)
    }

    private fun cancelSlowDim() {
        dimRunnable?.let { handler.removeCallbacks(it) }
        dimRunnable = null
    }
}
