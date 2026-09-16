package institute.castalia.atlas.player.sky

import android.os.Handler
import android.os.Looper
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import institute.castalia.atlas.player.audio.NocturneSynth
import institute.castalia.atlas.player.data.AppDatabase
import institute.castalia.atlas.player.data.Lesson
import institute.castalia.atlas.player.sky.SkyMath
import kotlin.concurrent.thread

class SkyTour(
    private val db: AppDatabase,
    private val player: Player,
    private val skyView: SkyView,
    private val nocturne: NocturneSynth,
    private val band: Int,
    private val featured: String? = null,
    private val onFinish: () -> Unit = {}
) {

    private data class Stop(val constellations: List<String>, val lessons: List<Lesson>)

    private val handler = Handler(Looper.getMainLooper())
    private val stops = ArrayList<Stop>()
    private var idx = -1
    private var running = false
    private var pending: Runnable? = null
    private var pace = 1f
    private val lessonsAllowed: Boolean = try {
        val cal = java.util.Calendar.getInstance()
        institute.castalia.atlas.player.Settings.lessonWindowOpen(
            skyView.context,
            cal.get(java.util.Calendar.HOUR_OF_DAY) * 60 + cal.get(java.util.Calendar.MINUTE)
        )
    } catch (e: Exception) {
        true
    }

    private val endListener = object : Player.Listener {
        override fun onPlaybackStateChanged(state: Int) {
            if (running && state == Player.STATE_ENDED) holdThenNext(4_000L)
        }
    }

    fun start() {
        if (running) return
        running = true
        if (!lessonsAllowed) {
            player.stop()
            player.clearMediaItems()
        }
        player.addListener(endListener)
        thread {
            val all = db.lessons().all()
                .filter { it.subject == "sky" && it.band == band }
            val stops = ArrayList<Stop>()
            stops.add(Stop(emptyList(), emptyList()))
            if (featured != null) {
                val mine = all
                    .filter { constellationsFor(it.title).contains(featured) }
                    .sortedBy { it.durationSec }
                val pair = constellationsFor(
                    mine.firstOrNull()?.title ?: featured
                )
                if (mine.isNotEmpty()) {
                    stops.add(Stop(pair, mine))
                } else {
                    all.sortedBy { it.durationSec }.forEach {
                        stops.add(Stop(constellationsFor(it.title), listOf(it)))
                    }
                }
            } else {
                all.sortedBy { it.durationSec }.forEach {
                    stops.add(Stop(constellationsFor(it.title), listOf(it)))
                }
            }
            stops.add(Stop(emptyList(), emptyList()))
            if (!lessonsAllowed) {
                for (i in stops.indices) stops[i] = Stop(stops[i].constellations, emptyList())
            }
            val now0 = System.currentTimeMillis()
            var nat = 0L
            stops.forEachIndexed { i, s ->
                if (s.constellations.isEmpty()) {
                    nat += if (s.lessons.isEmpty()) (if (i == 0) 10_000L else 8_000L)
                    else s.lessons[0].durationSec * 1000L + 4_000L
                } else {
                    nat += 17_000L + (s.lessons.firstOrNull()?.durationSec?.times(1000L) ?: 0L) + 4_000L
                }
            }
            try {
                val ctx = skyView.context
                val dawn = SkyMath.nextDawnMs(
                    java.util.Calendar.getInstance(),
                    institute.castalia.atlas.player.Settings.skyLat(ctx).toDouble(),
                    institute.castalia.atlas.player.Settings.skyLon(ctx).toDouble()
                )
                if (dawn > now0 && nat > 0) {
                    pace = ((dawn - now0).toFloat() / nat).coerceIn(1f, 8f)
                }
            } catch (e: Exception) {
            }
            handler.post {
                if (!running) return@post
                this.stops.clear()
                this.stops.addAll(stops)
                next()
            }
        }
    }

    fun stop() {
        if (!running) return
        running = false
        pending?.let { handler.removeCallbacks(it) }
        pending = null
        player.removeListener(endListener)
        skyView.post {
            skyView.setTour(null, 0)
            skyView.resetCamera()
        }
    }

    private fun next() {
        if (!running) return
        idx++
        if (idx >= stops.size) {
            running = false
            skyView.setTour(null, 0)
            onFinish()
            return
        }
        val stop = stops[idx]
        val primary = stop.constellations.firstOrNull()
        val extra = stop.constellations.getOrNull(1)
        if (primary == null) {
            skyView.setTour(null, 0)
            if (stop.lessons.isEmpty()) {
                holdThenNext(if (idx == 0) 10_000L else 8_000L)
            } else {
                play(stop.lessons[0], 1)
            }
            return
        }
        skyView.setTour(primary, 1, extra)
        schedule({
            skyView.setTour(primary, 2, extra)
            schedule({ count(stop) }, 5_000L)
        }, 5_000L)
    }

    private fun count(stop: Stop) {
        val total = skyView.countTotal()
        fun step(i: Int) {
            if (!running) return
            if (i >= total) {
                if (stop.lessons.isEmpty()) holdThenNext(12_000L) else play(stop.lessons[0], 0)
                return
            }
            skyView.setTour(stop.constellations.first(), 3, stop.constellations.getOrNull(1))
            skyView.setCountIndex(i)
            if (lessonsAllowed) nocturne.pluck(i)
            schedule({ step(i + 1) }, (1_400L * minOf(pace, 2f)).toLong())
        }
        step(0)
    }

    private var lessonIdx = 0

    private fun play(lesson: Lesson?, nextLesson: Int) {
        if (!lessonsAllowed || lesson == null) {
            holdThenNext(12_000L)
            return
        }
        player.setMediaItem(MediaItem.fromUri(lesson.filePath))
        player.prepare()
        player.volume = 0.55f
        player.play()
    }

    private fun play(lesson: Lesson?) {
        if (!lessonsAllowed || lesson == null) {
            holdThenNext(12_000L)
            return
        }
        player.setMediaItem(MediaItem.fromUri(lesson.filePath))
        player.prepare()
        player.volume = 0.55f
        player.play()
    }

    private fun holdThenNext(ms: Long) {
        val cons = stops.getOrNull(idx)?.constellations
        skyView.setTour(cons?.firstOrNull(), 0, cons?.getOrNull(1))
        schedule({ next() }, (ms * pace).toLong())
    }

    private fun schedule(r: Runnable, ms: Long) {
        pending?.let { handler.removeCallbacks(it) }
        pending = r
        handler.postDelayed(r, ms)
    }

    companion object {
        private val CONSTELLATIONS = listOf(
            "orion" to listOf("Orion"),
            "cassiopeia" to listOf("Cassiopeia", "Andromeda"),
            "queen" to listOf("Cassiopeia", "Andromeda"),
            "little bear" to listOf("Ursa Minor"),
            "north star" to listOf("Ursa Minor"),
            "polaris" to listOf("Ursa Minor"),
            "great bear" to listOf("Ursa Major", "Ursa Minor"),
            "big bear" to listOf("Ursa Major", "Ursa Minor"),
            "bear" to listOf("Ursa Major", "Ursa Minor"),
            "dipper" to listOf("Ursa Major"),
            "scorpion" to listOf("Scorpius"),
            "scorpius" to listOf("Scorpius"),
            "swan" to listOf("Cygnus"),
            "cygnus" to listOf("Cygnus"),
            "harp" to listOf("Lyra"),
            "lyra" to listOf("Lyra"),
            "seven sisters" to listOf("Taurus"),
            "taurus" to listOf("Taurus"),
            "pegasus" to listOf("Pegasus"),
            "winged" to listOf("Pegasus"),
            "horse" to listOf("Pegasus"),
            "princess" to listOf("Andromeda"),
            "andromeda" to listOf("Andromeda", "Cassiopeia")
        )

        fun constellationsFor(title: String): List<String> {
            val t = title.lowercase()
            return CONSTELLATIONS.firstOrNull { t.contains(it.first) }?.second ?: emptyList()
        }
    }
}
