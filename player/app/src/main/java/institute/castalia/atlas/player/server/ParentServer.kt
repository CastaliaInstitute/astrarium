package institute.castalia.atlas.player.server

import android.content.Context
import fi.iki.elonen.NanoHTTPD
import institute.castalia.atlas.player.Settings
import institute.castalia.atlas.player.astro.Astro
import institute.castalia.atlas.player.audio.AudioMonitor
import institute.castalia.atlas.player.data.AppDatabase
import institute.castalia.atlas.player.data.Lesson
import institute.castalia.atlas.player.data.QueueItem
import institute.castalia.atlas.player.sleep.SleepGuide
import org.json.JSONArray
import org.json.JSONObject
import java.io.InputStream
import java.util.Calendar

class ParentServer(
    private val ctx: Context,
    private val db: AppDatabase,
    private val sleepGuide: SleepGuide,
    private val monitor: AudioMonitor
) : NanoHTTPD(PORT) {

    override fun serve(session: IHTTPSession): Response {
        if (session.method == Method.OPTIONS) {
            return cors(newFixedLengthResponse(Response.Status.OK, MIME_PLAINTEXT, ""))
        }
        return try {
            val r = if (session.uri.startsWith("/api/")) api(session) else static(session.uri)
            cors(r)
        } catch (e: Exception) {
            cors(newFixedLengthResponse(Response.Status.INTERNAL_ERROR, MIME_PLAINTEXT, e.toString()))
        }
    }

    private fun cors(r: Response): Response {
        r.addHeader("Access-Control-Allow-Origin", "*")
        r.addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        r.addHeader("Access-Control-Allow-Headers", "Content-Type")
        return r
    }

    private fun api(session: IHTTPSession): Response {
        val body = if (session.method == Method.POST) {
            val parsed = HashMap<String, String>()
            session.parseBody(parsed)
            parsed["postData"] ?: ""
        } else ""
        val json = when (session.uri) {
            "/api/lessons" -> lessons(session.parameters["band"]?.firstOrNull()?.toIntOrNull())
            "/api/lessons/import" -> when (session.method) {
                Method.POST -> importLessons(body)
                else -> errorJson()
            }
            "/api/queue" -> when (session.method) {
                Method.GET -> queueJson()
                Method.POST -> {
                    replaceQueue(body)
                    queueJson()
                }
                else -> errorJson()
            }
            "/api/settings" -> when (session.method) {
                Method.POST -> {
                    saveSettings(body)
                    settingsJson()
                }
                else -> settingsJson()
            }
            "/api/wake" -> when (session.method) {
                Method.POST -> {
                    sleepGuide.wake()
                    status()
                }
                else -> errorJson()
            }
            "/api/astro" -> astro()
            "/api/status" -> status()
            "/api/sleep/start" -> when (session.method) {
                Method.POST -> {
                    sleepGuide.start()
                    status()
                }
                else -> errorJson()
            }
            "/api/sky" -> when (session.method) {
                Method.POST -> {
                    sleepGuide.skyNow()
                    status()
                }
                else -> errorJson()
            }
            "/api/skyview" -> when (session.method) {
                Method.GET -> sleepGuide.debugSkyJson()
                Method.POST -> {
                    val s = JSONObject(body)
                    sleepGuide.debugSky(
                        if (s.isNull("name")) null else s.getString("name"),
                        s.optInt("stage", 0)
                    )
                    sleepGuide.debugSkyJson()
                }
                else -> errorJson()
            }
            "/api/align" -> when (session.method) {
                Method.GET -> alignJson()
                Method.POST -> {
                    val s = JSONObject(body)
                    val windows = ArrayList<institute.castalia.atlas.player.sky.StarField3D.SkyWindow>()
                    val arr = s.optJSONArray("windows")
                    if (arr != null) {
                        for (i in 0 until arr.length()) {
                            val w = arr.getJSONObject(i)
                            val q = w.getJSONArray("quad")
                            val quad = FloatArray(8)
                            for (j in 0 until 8) quad[j] = q.getDouble(j).toFloat()
                            windows.add(
                                institute.castalia.atlas.player.sky.StarField3D.SkyWindow(
                                    quad, w.optString("dir", "F")
                                )
                            )
                        }
                    }
                    sleepGuide.setAlign(s.optString("mode", "sky"), windows)
                    alignJson()
                }
                else -> errorJson()
            }
            "/api/align/pattern" -> when (session.method) {
                Method.POST -> {
                    val s = JSONObject(body)
                    sleepGuide.setAlignPattern(s.optBoolean("on", true))
                    status()
                }
                else -> errorJson()
            }
            "/api/debug/dest" -> when (session.method) {
                Method.POST -> {
                    val s = JSONObject(body)
                    sleepGuide.setDebugAtDest(s.optBoolean("on", true))
                    status()
                }
                else -> errorJson()
            }
            "/api/debug/timescale" -> when (session.method) {
                Method.POST -> {
                    val s = JSONObject(body)
                    sleepGuide.setTimeScale(s.optDouble("x", 1.0).toFloat())
                    status()
                }
                else -> errorJson()
            }
            else -> errorJson()
        }
        return newFixedLengthResponse(Response.Status.OK, "application/json", json.toString())
    }

    private fun lessons(band: Int?): JSONArray {
        val list = if (band == null || band < 0) db.lessons().all() else db.lessons().byBand(band)
        return JSONArray().apply {
            list.forEach {
                put(
                    JSONObject()
                        .put("id", it.id)
                        .put("title", it.title)
                        .put("band", it.band)
                        .put("subject", it.subject)
                        .put("durationSec", it.durationSec)
                )
            }
        }
    }

    private fun importLessons(body: String): JSONObject {
        val arr = JSONObject(body).getJSONArray("lessons")
        val rows = (0 until arr.length()).map { i ->
            val l = arr.getJSONObject(i)
            Lesson(
                id = l.getLong("id"),
                title = l.getString("title"),
                band = l.getInt("band"),
                subject = l.getString("subject"),
                filePath = l.getString("filePath"),
                durationSec = l.optInt("durationSec", 30)
            )
        }
        db.runInTransaction { db.lessons().upsertAll(rows) }
        return JSONObject().put("imported", rows.size)
    }

    private fun queueJson(): JSONArray = JSONArray().apply {
        db.queue().all().forEach { put(it.lessonId) }
    }

    private fun replaceQueue(body: String) {
        val ids = JSONObject(body).getJSONArray("lessonIds")
        db.runInTransaction {
            db.queue().clear()
            db.queue().insertAll(
                (0 until ids.length()).map {
                    QueueItem(lessonId = ids.getLong(it), position = it)
                }
            )
        }
    }

    private fun saveSettings(body: String) {
        val s = JSONObject(body)
        s.optInt("bedtimeMinutes", -1).takeIf { it >= 0 }?.let { Settings.setBedtimeMinutes(ctx, it) }
        s.optInt("sessionCap", -1).takeIf { it > 0 }?.let { Settings.setSessionCapMinutes(ctx, it) }
        s.optInt("musicMinutes", -1).takeIf { it > 0 }?.let { Settings.setMusicMinutes(ctx, it) }
        s.optInt("fadeMinutes", -1).takeIf { it > 0 }?.let { Settings.setFadeMinutes(ctx, it) }
        s.optDouble("nightBrightness", -1.0).takeIf { it >= 0 }
            ?.let { Settings.setNightBrightness(ctx, it.toFloat()) }
        s.optDouble("sootheBrightness", -1.0).takeIf { it >= 0 }
            ?.let { Settings.setSootheBrightness(ctx, it.toFloat()) }
        s.optDouble("arousalThreshold", -1.0).takeIf { it >= 0 }
            ?.let { Settings.setArousalThreshold(ctx, it.toFloat()) }
        s.optDouble("skyLat", 999.0).takeIf { it != 999.0 }
            ?.let { Settings.setSkyLat(ctx, it.toFloat()) }
        s.optDouble("skyLon", 999.0).takeIf { it != 999.0 }
            ?.let { Settings.setSkyLon(ctx, it.toFloat()) }
        s.optDouble("skyBottomAz", -1.0).takeIf { it >= 0 }
            ?.let { Settings.setSkyBottomAz(ctx, it.toFloat()) }
        s.optDouble("skyMagLimit", -1.0).takeIf { it >= 0 }
            ?.let { Settings.setSkyMagLimit(ctx, it.toFloat()) }
        s.optInt("speakerVolume", -1).takeIf { it >= 0 }
            ?.let { Settings.setSpeakerVolume(ctx, it) }
        if (s.has("skyMirror")) Settings.setSkyMirror(ctx, s.getBoolean("skyMirror"))
        s.optInt("activeBand", -1).takeIf { it >= 0 }?.let { Settings.setActiveBand(ctx, it) }
        s.optInt("amberAlpha", -1).takeIf { it >= 0 }?.let { Settings.setAmberAlpha(ctx, it) }
        if (s.has("kiosk")) Settings.setKiosk(ctx, s.getBoolean("kiosk"))
        if (s.has("monitorEnabled")) Settings.setMonitorEnabled(ctx, s.getBoolean("monitorEnabled"))
        if (s.has("skyDuringMusic")) Settings.setSkyDuringMusic(ctx, s.getBoolean("skyDuringMusic"))
        if (s.has("skyMode")) Settings.setSkyMode(ctx, s.getString("skyMode"))
        if (s.has("nocturneEnabled")) Settings.setNocturneEnabled(ctx, s.getBoolean("nocturneEnabled"))
        if (s.has("showLabels")) Settings.setShowLabels(ctx, s.getBoolean("showLabels"))
        s.optInt("lessonWindowMinutes", -1).takeIf { it >= 0 }?.let { Settings.setLessonWindowMinutes(ctx, it) }
        sleepGuide.applyLiveSettings()
    }

    private fun settingsJson(): JSONObject = JSONObject()
        .put("bedtimeMinutes", Settings.bedtimeMinutes(ctx))
        .put("sessionCap", Settings.sessionCapMinutes(ctx))
        .put("musicMinutes", Settings.musicMinutes(ctx))
        .put("fadeMinutes", Settings.fadeMinutes(ctx))
        .put("nightBrightness", Settings.nightBrightness(ctx).toDouble())
        .put("sootheBrightness", Settings.sootheBrightness(ctx).toDouble())
        .put("arousalThreshold", Settings.arousalThreshold(ctx).toDouble())
        .put("skyLat", Settings.skyLat(ctx).toDouble())
        .put("skyLon", Settings.skyLon(ctx).toDouble())
        .put("skyBottomAz", Settings.skyBottomAz(ctx).toDouble())
        .put("skyMagLimit", Settings.skyMagLimit(ctx).toDouble())
        .put("skyMirror", Settings.skyMirror(ctx))
        .put("speakerVolume", Settings.speakerVolume(ctx))
        .put("amberAlpha", Settings.amberAlpha(ctx))
        .put("kiosk", Settings.kiosk(ctx))
        .put("monitorEnabled", Settings.monitorEnabled(ctx))
        .put("skyDuringMusic", Settings.skyDuringMusic(ctx))
        .put("skyMode", Settings.skyMode(ctx))
        .put("nocturneEnabled", Settings.nocturneEnabled(ctx))
        .put("showLabels", Settings.showLabels(ctx))
        .put("lessonWindowMinutes", Settings.lessonWindowMinutes(ctx))

    private fun status(): JSONObject {
        val now = Calendar.getInstance()
        return JSONObject()
            .put("phase", sleepGuide.phase.name)
            .put("nowMinutes", now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE))
            .put("micLevel", monitor.lastLevel)
            .put("micWatch", monitor.watchFor.name)
            .put("freeBytes", ctx.getExternalFilesDir(null)?.usableSpace ?: 0L)
            .put("appVersion", "0.1.0")
            .put("settings", settingsJson())
    }

    private fun astro(): JSONObject {
        val s = Astro.snapshot(Calendar.getInstance())
        return JSONObject()
            .put("moon", JSONObject()
                .put("sign", s.moon.sign)
                .put("phase", s.moonPhase)
                .put("illum", s.moonIllum))
            .put("sun", JSONObject().put("sign", s.sun.sign))
            .put("planets", JSONArray().apply {
                s.planets.forEach { put(JSONObject().put("name", it.name).put("sign", it.sign)) }
            })
            .put("aspects", JSONArray().apply {
                s.aspects.forEach {
                    put(JSONObject().put("a", it.a).put("b", it.b).put("type", it.type).put("orb", it.orbDeg))
                }
            })
    }

    private fun errorJson(): JSONObject = JSONObject().put("error", "method not allowed")

    private fun alignJson(): JSONObject = sleepGuide.alignState()

    private fun static(uri: String): Response {
        val path = when {
            uri == "/align" || uri == "/align/" -> "pwa/align.html"
            else -> uri.trimStart('/').ifEmpty { "index.html" }
        }
        val mime = when (path.substringAfterLast('.')) {
            "html" -> "text/html"
            "js" -> "application/javascript"
            "css" -> "text/css"
            "svg" -> "image/svg+xml"
            "webmanifest", "json" -> "application/manifest+json"
            else -> "application/octet-stream"
        }
        val stream: InputStream = ctx.assets.open(path)
        return newChunkedResponse(Response.Status.OK, mime, stream)
    }

    companion object {
        private const val PORT = 8080

        @Volatile
        private var server: ParentServer? = null

        fun start(ctx: Context, db: AppDatabase, sleepGuide: SleepGuide, monitor: AudioMonitor) {
            if (server == null) synchronized(this) {
                if (server == null) {
                    server = ParentServer(ctx.applicationContext, db, sleepGuide, monitor)
                    server?.start(5_000, false)
                }
            }
        }
    }
}
