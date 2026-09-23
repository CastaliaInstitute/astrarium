package institute.castalia.atlas.player.sky

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.view.View
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.sin
import kotlin.math.sqrt

class StarField3D(context: Context) : View(context) {

    private data class Star3D(val x: Double, val y: Double, val z: Double, val mag: Double, val ci: Double, val absM: Double, val r70Sq: Double, val r65Sq: Double)
    private data class NamedStar(val name: String, val x: Double, val y: Double, val z: Double)
    private data class Wp(val name: String, val constellation: String, val x: Double, val y: Double, val z: Double)

    private data class Planet(
        val name: String,
        val bmp: String,
        val baseR: Float,
        val ring: Boolean = false,
        val subtitle: String = "",
        val exagDistPc: Double = 0.1,
        val radiusKm: Double = 0.0
    )

    private fun trueRadiusPx(name: String, radiusKm: Double, focal: Float): Float {
        if (radiusKm <= 0.0) return 0f
        val cal = Calendar.getInstance()
        val distKm = when (name) {
            "Moon" -> SolarSystem.moonDistance(cal) * 0.2725  // center-to-center ≈ surface fixup ignored
            "Earth" -> 0.0
            else -> SolarSystem.planetDistanceAu(name, cal) * 1.495978707e8
        }
        if (distKm <= 0.0 || distKm.isNaN()) return 0f
        val ang = Math.atan2(radiusKm, distKm)
        return (focal * Math.tan(ang)).toFloat()
    }

    private var stars: List<Star3D> = emptyList()
    private val labels = ArrayList<NamedStar>()
    private val starRoute = ArrayList<Wp>()
    private val waypoints = ArrayList<Wp>()
    private val planetBmp = HashMap<String, android.graphics.Bitmap>()
    private val planetPos = HashMap<String, Triple<Double, Double, Double>>()
    private var ringBmp: android.graphics.Bitmap? = null
    private val bmpPaint = Paint(android.graphics.Paint.FILTER_BITMAP_FLAG)
    private var loaded = false

    private var camX = 0.0
    private var camY = 0.0
    private var camZ = 0.0
    private var lastFrame = 0L
    private var elapsed = 0.0
    private var running = false
    private var wpIndex = 0
    private var pauseUntil = 0L
    private var arrivalName: String? = null
    private var arrivalConst: String? = null
    private var curSpeed = 0.0
    private var homeStage = 0
    private var yaw180 = false
    private var legMs = 60_000L
    private var legTravelMs = 45_000L
    private var pauseMs = 16_000L
    private var journeyEnd = 0L
    private var midnight = 0L
    private var outboundStart = 0L
    private var returnStart = 0L
    private var destWp: Wp? = null

    data class SkyWindow(val quad: FloatArray, val dir: String)
    private var alignMode = "sky"
    private val alignWindows = ArrayList<SkyWindow>()
    private val windowBmps = HashMap<SkyWindow, android.graphics.Bitmap>()
    var alignPattern = false
    var debugAtDest = false

    // debug: compress the anchored journey timeline so it plays from departure
    private var timeScale = 1f
    @Volatile
    private var timeAnchor = 0L

    fun setTimeScale(scale: Float) {
        timeScale = scale
        timeAnchor = System.currentTimeMillis()
    }

    fun setAlign(mode: String, windows: List<SkyWindow>) {
        alignMode = if (windows.isEmpty()) "sky" else mode
        alignWindows.clear()
        alignWindows.addAll(windows)
        windowBmps.values.forEach { it.recycle() }
        windowBmps.clear()
        institute.castalia.atlas.player.Settings.setAlignJson(context, alignJson().toString())
        postInvalidate()
    }

    fun setPattern(on: Boolean) {
        alignPattern = on
        institute.castalia.atlas.player.Settings.setAlignJson(context, alignJson().toString())
        postInvalidate()
    }

    // camera basis (catalog frame): forward, up, right
    private var fX = 0.0; private var fY = 0.0; private var fZ = 1.0
    private var uX = 0.0; private var uY = 1.0; private var uZ = 0.0
    private var rX = 1.0; private var rY = 0.0; private var rZ = 0.0
    private var lookTX = 0.0; private var lookTY = 0.0; private var lookTZ = 1.0
    private var manualLookUntil = 0L
    private var lookYaw = 0.0
    private var lookPitch = 0.0

    // Sun's galactic-orbit velocity (~230 km/s toward l=86.4deg, b=0) in catalog-frame pc/s
    private val sunV: Triple<Double, Double, Double>
    private var journeyT0 = 0L

    init {
        val l = Math.toRadians(86.4)
        val g1 = kotlin.math.cos(l); val g2 = sin(l); val g3 = 0.0
        val ex = -0.0549 * g1 - 0.8734 * g2 - 0.4838 * g3
        val ey = 0.4941 * g1 - 0.4448 * g2 + 0.7470 * g3
        val ez = -0.8677 * g1 - 0.1981 * g2 + 0.4560 * g3
        val v = 230.0 / 3.085677581e13 // pc per second
        sunV = Triple(ex * v, ey * v, ez * v)
    }

    private fun earthPos(nowMs: Long): Triple<Double, Double, Double> {
        val el = (nowMs - journeyT0) / 1000.0
        return Triple(sunV.first * el, sunV.second * el, sunV.third * el)
    }

    // Orrery: true relative radii, proportional distances (AU × 0.04 pc; Moon pulled out to 0.02)
    private val AU_PC = 0.04
    private val SIZE_GAIN = 5.5e6
    private val planets = listOf(
        Planet("Earth", "earth", 10f, subtitle = "Home", radiusKm = 6371.0),
        Planet("Moon", "moon", 9f, subtitle = "Earth's companion", exagDistPc = 0.02, radiusKm = 1737.0),
        Planet("Venus", "venus", 9f, subtitle = "Morning star", exagDistPc = 0.72 * AU_PC, radiusKm = 6052.0),
        Planet("Mars", "mars", 9f, subtitle = "The red planet", exagDistPc = 1.52 * AU_PC, radiusKm = 3389.0),
        Planet("Jupiter", "jupiter", 15f, subtitle = "King of planets", exagDistPc = 5.2 * AU_PC, radiusKm = 69911.0),
        Planet("Saturn", "saturn", 13f, ring = true, subtitle = "Lord of the rings", exagDistPc = 9.54 * AU_PC, radiusKm = 58232.0)
    )

    init {
        try {
            val raw = context.assets.open("sky/stars3d.json").bufferedReader().readText()
            val root = JSONObject(raw)
            val arr = root.getJSONArray("stars")
            val base = ArrayList<Star3D>(arr.length())
            for (i in 0 until arr.length()) {
                val s = arr.getJSONArray(i)
                val x = s.getDouble(0)
                val y = s.getDouble(1)
                val z = s.getDouble(2)
                val mag = s.getDouble(3)
                val ci = s.getDouble(4)
                val d0 = sqrt(x * x + y * y + z * z).coerceAtLeast(1e-9)
                val absM = mag - 5 * (Math.log10(d0) - 1)
                base.add(Star3D(x, y, z, mag, ci, absM, rVisSq(absM, 7.0), rVisSq(absM, 6.5)))
            }
            stars = base
            val lab = root.getJSONArray("labels")
            for (i in 0 until lab.length()) {
                val l = lab.getJSONObject(i)
                labels.add(NamedStar(l.getString("n"), l.getDouble("x"), l.getDouble("y"), l.getDouble("z")))
            }
            labels.sortedBy { l -> sqrt(l.x * l.x + l.y * l.y + l.z * l.z) }.forEach {
                starRoute.add(Wp(it.name, "", it.x, it.y, it.z))
            }
            for (p in planets) {
                try {
                    context.assets.open("sky/planets/${p.bmp}.png").use {
                        android.graphics.BitmapFactory.decodeStream(it)
                    }?.let { bmp -> planetBmp[p.bmp] = bmp }
                } catch (e: Exception) {
                }
                try {
                    context.assets.open("sky/planets/${p.bmp}_globe.png").use {
                        android.graphics.BitmapFactory.decodeStream(it)
                    }?.let { bmp -> planetBmp[p.bmp + "_globe"] = bmp }
                } catch (e: Exception) {
                }
            }
            try {
                context.assets.open("sky/planets/saturn-ring.png").use {
                    ringBmp = android.graphics.BitmapFactory.decodeStream(it)
                }
            } catch (e: Exception) {
            }
            loaded = stars.isNotEmpty()
        } catch (e: Exception) {
            loaded = false
        }
        if (loaded) {
            // Gaia DR3 real-star expansion: binary floats parsed off the main thread
            kotlin.concurrent.thread {
                try {
                    val bytes = context.assets.open("sky/gaia3d.bin").readBytes()
                    val bb = java.nio.ByteBuffer.wrap(bytes).order(java.nio.ByteOrder.LITTLE_ENDIAN)
                    val n = bytes.size / 20
                    val extra = ArrayList<Star3D>(n)
                    for (i in 0 until n) {
                        val x = bb.getFloat().toDouble()
                        val y = bb.getFloat().toDouble()
                        val z = bb.getFloat().toDouble()
                        val absM = bb.getFloat().toDouble()
                        val ci = bb.getFloat().toDouble()
                        val d0 = sqrt(x * x + y * y + z * z).coerceAtLeast(1e-9)
                        extra.add(Star3D(x, y, z, absM + 5 * (Math.log10(d0) - 1), ci, absM, rVisSq(absM, 7.0), rVisSq(absM, 6.5)))
                    }
                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                        val all = ArrayList<Star3D>(stars.size + extra.size)
                        all.addAll(stars)
                        all.addAll(extra)
                        stars = all
                        android.util.Log.d("StarField3D", "gaia loaded: ${extra.size} real, ${all.size} total")
                        postInvalidate()
                    }
} catch (e: Exception) {
            }
        }
        try {
            context.assets.open("sky/galactex.png").use { st ->
                mwBmp = android.graphics.BitmapFactory.decodeStream(st)
            }
            android.util.Log.d("StarField3D", "milky way texture loaded")
            val bmp = mwBmp
            if (bmp != null) {
                kotlin.concurrent.thread {
                    val band = buildBand()
                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                        bandSegs = band
                        postInvalidate()
                    }
                }
            }
        } catch (e: Exception) {
            mwBmp = null
        }
        kotlin.concurrent.thread {
            try {
                val root = JSONObject(context.assets.open("sky/constellations3d.json").bufferedReader().readText())
                val figs = ArrayList<ConsFig>()
                val arr = root.getJSONArray("figs")
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val polys = o.getJSONArray("poly")
                    val segList = ArrayList<Float>()
                    for (j in 0 until polys.length()) {
                        val line = polys.getJSONArray(j)
                        for (k in 0 until line.length() - 1) {
                            val a = line.getJSONArray(k)
                            val b = line.getJSONArray(k + 1)
                            segList.add(a.getDouble(0).toFloat()); segList.add(a.getDouble(1).toFloat()); segList.add(a.getDouble(2).toFloat())
                            segList.add(b.getDouble(0).toFloat()); segList.add(b.getDouble(1).toFloat()); segList.add(b.getDouble(2).toFloat())
                        }
                    }
                    if (segList.isNotEmpty()) figs.add(ConsFig(o.getString("n"), segList.toFloatArray()))
                }
                val arts = ArrayList<ArtFig>()
                val artRoot = JSONArray(context.assets.open("sky/art.json").bufferedReader().readText())
                for (i in 0 until artRoot.length()) {
                    val o = artRoot.getJSONObject(i)
                    val pts = o.getJSONArray("pts")
                    val fl = FloatArray(pts.length() * 4)
                    for (k in 0 until pts.length()) {
                        val p = pts.getJSONArray(k)
                        fl[k * 4] = p.getDouble(0).toFloat()
                        fl[k * 4 + 1] = p.getDouble(1).toFloat()
                        fl[k * 4 + 2] = p.getDouble(2).toFloat()
                        fl[k * 4 + 3] = p.getDouble(3).toFloat()
                    }
                    arts.add(ArtFig(o.getString("image"), o.getInt("w"), o.getInt("h"), fl))
                }
                android.os.Handler(android.os.Looper.getMainLooper()).post {
                    consFigs = figs
                    artFigs = arts
                    android.util.Log.d("StarField3D", "constellations: ${figs.size} figs, ${arts.size} art")
                    postInvalidate()
                }
            } catch (e: Exception) {
                android.util.Log.w("StarField3D", "cons load failed: ${e.message}")
            }
        }
        try {
            val saved = institute.castalia.atlas.player.Settings.alignJson(context)
            if (saved.isNotEmpty()) {
                val j = JSONObject(saved)
                alignMode = j.optString("mode", "sky")
                alignPattern = j.optBoolean("pattern", false)
                val wins = j.optJSONArray("windows")
                if (wins != null) {
                    for (i in 0 until wins.length()) {
                        val o = wins.getJSONObject(i)
                        val q = o.getJSONArray("quad")
                        val fa = FloatArray(8) { q.getDouble(it).toFloat() }
                        alignWindows.add(SkyWindow(fa, o.getString("dir")))
                    }
                }
                android.util.Log.d("StarField3D", "align restored: windows=${alignWindows.size}")
            }
        } catch (e: Exception) {
        }
    }
    }

    private val density = resources.displayMetrics.density
    private val starPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var mwBmp: android.graphics.Bitmap? = null
    private var bandSegs: FloatArray? = null
    private val bandPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x3DB9D4FF.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 1.0f * density
    }
    private val artPaint3D = Paint().apply { isFilterBitmap = true }
    private val artBmpCache = HashMap<String, android.graphics.Bitmap>()
    private var consFigs: List<ConsFig> = emptyList()
    private var artFigs: List<ArtFig> = emptyList()
    var showLines = institute.castalia.atlas.player.Settings.constellationLines(context)
        private set
    var showArt = institute.castalia.atlas.player.Settings.constellationArt(context)
        private set

    private class ConsFig(val name: String, val segs: FloatArray)

    private class ArtFig(val image: String, val w: Int, val h: Int, val pts: FloatArray)
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xCCF2B25C.toInt()
        textSize = 13f * density
    }
    private val footerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xEAF2B25C.toInt()
        textSize = 12f * density
    }
    private val crossPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xE6F2B25C.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 1.6f * density
    }
    private val bigPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFF2B25C.toInt()
        textSize = 20f * density
        textAlign = Paint.Align.CENTER
    }
    private val navPaintL = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFF2B25C.toInt()
        textSize = 13f * density
    }
    private val navPaintR = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFF2B25C.toInt()
        textSize = 13f * density
        textAlign = Paint.Align.RIGHT
    }
    private val subPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xAA9AA3C0.toInt()
        textSize = 12f * density
        textAlign = Paint.Align.CENTER
    }
    private val yearPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFF2B25C.toInt()
        textSize = 15f * density
        textAlign = Paint.Align.CENTER
    }
    private val dimBuckets = Array(16) { FloatArray(6000 * 2) }
    private val dimCount = IntArray(16)
    private val CLASS_BV = doubleArrayOf(-0.33, 0.0, 0.3, 0.58, 0.81, 1.4, 1.9, 2.6)
    private val dimPaints = Array(16) { Paint().apply {
        strokeWidth = 1.4f * density
        strokeCap = Paint.Cap.ROUND
        color = starColor(CLASS_BV[it / 2])
    } }

    fun start() {
        if (running || !loaded) return
        running = true
        start(0L)
    }

    fun start(journeyEndMs: Long) {
        start(journeyEndMs, 0L, 0L, null)
    }

    fun start(journeyEndMs: Long, midnightMs: Long, outboundStartMs: Long, destConstellation: String?, figStars: List<Pair<Double, Double>>? = null) {
        if (!loaded) return
        running = true
        camX = 0.0
        camY = 0.0
        camZ = 0.0
        elapsed = 0.0
        wpIndex = 0
        pauseUntil = 0L
        arrivalName = null
        arrivalConst = null
        homeStage = 0
        yaw180 = false
        planetPos.clear()
        waypoints.clear()
        val cal = Calendar.getInstance()
        val moon = SolarSystem.moon(cal)
        planetPos["Moon"] = cartOf(moon.raDeg, moon.decDeg, planets[0].exagDistPc)
        for (p in SolarSystem.planets(cal)) {
            planets.firstOrNull { it.name == p.name }?.let { def ->
                planetPos[p.name] = cartOf(p.raDeg, p.decDeg, def.exagDistPc)
            }
        }
        planetPos["Earth"] = Triple(0.0, 0.0, 0.0)
        journeyEnd = journeyEndMs
        midnight = if (midnightMs > 0) midnightMs else 0L
        outboundStart = outboundStartMs
        returnStart = if (midnightMs > 0) midnightMs + STAY_MS else 0L
        destWp = destStarWp(destConstellation, figStars)
        journeyT0 = if (midnight > 0) outboundStart else System.currentTimeMillis()
        android.util.Log.d(
            "StarField3D",
            "dest=${destWp?.name ?: "GENERIC"} dist=${destWp?.let { sqrt(it.x * it.x + it.y * it.y + it.z * it.z) * 3.26156 } ?: 0.0} ly"
        )
        arrivalName = null

        val now = System.currentTimeMillis()
        if (destWp != null && midnight > now) {
            waypoints.add(destWp!!)
        } else {
            val slowTour = journeyEndMs > now + 30 * 60_000L
            waypoints.addAll(planetWps())
            waypoints.addAll(if (slowTour) starRoute.take(18) else starRoute)
        }
        if (destWp != null && midnight > 0) {
            val cd = cappedDest()
            when {
                now < midnight -> {
                    homeStage = 0
                    yaw180 = false
                    val span = (midnight - outboundStart).coerceAtLeast(60_000L)
                    val p = ((now - outboundStart).toDouble() / span).coerceIn(0.0, 1.0)
                    camX = cd.first * p
                    camY = cd.second * p
                    camZ = cd.third * p
                }
                now < returnStart -> {
                    homeStage = 1
                    yaw180 = true
                    camX = cd.first
                    camY = cd.second
                    camZ = cd.third
                    arrivalName = destWp!!.name
                    arrivalConst = destWp!!.constellation
                    pauseUntil = returnStart
                }
                else -> {
                    homeStage = 2
                    yaw180 = true
                    val span = (journeyEnd - returnStart).coerceAtLeast(60_000L)
                    val p = ((now - returnStart).toDouble() / span).coerceIn(0.0, 1.0)
                    camX = cd.first * (1 - p)
                    camY = cd.second * (1 - p)
                    camZ = cd.third * (1 - p)
                }
            }
        } else {
            val hoursToDawn = journeyEndMs > now + 30 * 60_000L
            legMs = if (hoursToDawn) (journeyEndMs - now - 30 * 60_000L) / (waypoints.size + 1).coerceAtLeast(1) else 0L
            legTravelMs = if (hoursToDawn) (legMs * 0.6).toLong().coerceAtLeast(30_000L) else 6_000L
            pauseMs = if (hoursToDawn) (legMs * 0.4).toLong().coerceAtLeast(60_000L) else 4_000L
        }
        lastFrame = System.currentTimeMillis()
        postInvalidateOnAnimation()
    }

    private fun planetWps(): List<Wp> {
        val out = ArrayList<Wp>()
        for (p in planets) {
            planetPos[p.name]?.let {
                out.add(Wp(p.name, p.subtitle, it.first, it.second, it.third))
            }
        }
        return out
    }

    private fun galactic(x: Double, y: Double, z: Double): Pair<Double, Double> {
        val d = sqrt(x * x + y * y + z * z).coerceAtLeast(1e-9)
        val g1 = -0.0549 * x - 0.8734 * y - 0.4838 * z
        val g2 = 0.4941 * x - 0.4448 * y + 0.7470 * z
        val g3 = -0.8677 * x - 0.1981 * y + 0.4560 * z
        var l = Math.toDegrees(kotlin.math.atan2(g2 / d, g1 / d))
        if (l < 0) l += 360.0
        val b = Math.toDegrees(kotlin.math.asin((g3 / d).coerceIn(-1.0, 1.0)))
        return Pair(l, b)
    }

    private fun destStarWp(constellation: String?, figStars: List<Pair<Double, Double>>?): Wp? {
        if (constellation == null) return null
        val father = FATHER_STAR[constellation]
        if (father != null) {
            labels.firstOrNull { it.name == father }?.let {
                return Wp(it.name, constellation, it.x, it.y, it.z)
            }
        }
        if (figStars != null && figStars.isNotEmpty()) {
            var best: Star3D? = null
            var bestD = Double.MAX_VALUE
            for ((raDeg, decDeg) in figStars) {
                val ra = Math.toRadians(raDeg)
                val dec = Math.toRadians(decDeg)
                val ux = kotlin.math.cos(dec) * kotlin.math.cos(ra)
                val uy = kotlin.math.cos(dec) * kotlin.math.sin(ra)
                val uz = kotlin.math.sin(dec)
                for (s in stars) {
                    val d = sqrt(s.x * s.x + s.y * s.y + s.z * s.z).coerceAtLeast(1e-9)
                    if (d >= bestD || d > 2000.0) continue
                    val dot = (s.x * ux + s.y * uy + s.z * uz) / d
                    if (dot > 0.9995) {
                        best = s
                        bestD = d
                    }
                }
            }
            best?.let {
                val named = labels.firstOrNull { l ->
                    val dx = l.x - it.x
                    val dy = l.y - it.y
                    val dz = l.z - it.z
                    sqrt(dx * dx + dy * dy + dz * dz) < 0.5
                }
                return Wp(named?.name ?: constellation, constellation, it.x, it.y, it.z)
            }
        }
        return null
    }

    private fun cappedDest(): Triple<Double, Double, Double> {
        val wp = destWp ?: return Triple(0.0, 0.0, 0.0)
        val d = sqrt(wp.x * wp.x + wp.y * wp.y + wp.z * wp.z)
        val s = if (d <= TRAVEL_CAP_PC) 1.0 else TRAVEL_CAP_PC / d
        return Triple(wp.x * s, wp.y * s, wp.z * s)
    }

    private fun cartOf(raDeg: Double, decDeg: Double, distPc: Double): Triple<Double, Double, Double> {
        val ra = Math.toRadians(raDeg)
        val dec = Math.toRadians(decDeg)
        val d = distPc
        return Triple(d * kotlin.math.cos(dec) * kotlin.math.cos(ra), d * kotlin.math.cos(dec) * kotlin.math.sin(ra), d * kotlin.math.sin(dec))
    }

    fun stop() {
        running = false
    }

    val isRunning: Boolean
        get() = running

    override fun onDraw(canvas: Canvas) {
        if (!loaded) return
        val now = System.currentTimeMillis()
        val dt = ((now - lastFrame).coerceAtLeast(16)) / 1000.0
        lastFrame = now
        if (running) {
            elapsed += dt
            val anchored = destWp != null && midnight > 0L
            val machineNow = if (timeScale != 1f && anchored) {
                outboundStart + ((now - timeAnchor).toFloat() * timeScale).toLong()
            } else now
            val anchored2 = anchored
            if (debugAtDest && destWp != null) {
                val wp = destWp!!
                camX = wp.x; camY = wp.y; camZ = wp.z
                curSpeed = 0.0
                if (!manualLook()) { lookTX = -wp.x; lookTY = -wp.y; lookTZ = -wp.z }
                arrivalName = wp.name; arrivalConst = wp.constellation
                pauseUntil = Long.MAX_VALUE
            } else if (anchored2 && homeStage == 0) {
                // outbound: gentle drift toward the lesson star, capped so the sky stays recognizable
                val cd = cappedDest()
                if (!manualLook()) { lookTX = destWp!!.x; lookTY = destWp!!.y; lookTZ = destWp!!.z }
                val span = (midnight - outboundStart).coerceAtLeast(60_000L)
                val p = ((machineNow - outboundStart).toDouble() / span).coerceIn(0.0, 1.0)
                camX = cd.first * p
                camY = cd.second * p
                camZ = cd.third * p
                curSpeed = sqrt(cd.first * cd.first + cd.second * cd.second + cd.third * cd.third) / (span / 1000.0)
                if (machineNow >= midnight - 2_000L) {
                    camX = cd.first
                    camY = cd.second
                    camZ = cd.third
                    arrivalName = destWp!!.name
                    arrivalConst = destWp!!.constellation
                    homeStage = 1
                    yaw180 = true
                    pauseUntil = returnStart
                }
            } else if (anchored2 && homeStage == 1) {
                val cd = cappedDest()
                if (!manualLook()) { lookTX = -destWp!!.x; lookTY = -destWp!!.y; lookTZ = -destWp!!.z }
                camX = cd.first
                camY = cd.second
                camZ = cd.third
                curSpeed = 0.0
                if (machineNow >= returnStart) {
                    homeStage = 2
                    yaw180 = true
                }
            } else if (anchored2 && homeStage == 2) {
                // return: linear so 3am is just past halfway, easing only at the very end for the Earth approach
                // Earth drifts in the galactic frame while we travel, so we aim at where it will be
                val cd = cappedDest()
                val e = earthPos(machineNow)
                lookTX = e.first - camX; lookTY = e.second - camY; lookTZ = e.third - camZ
                val span = (journeyEnd - returnStart).coerceAtLeast(60_000L)
                val p = ((machineNow - returnStart).toDouble() / span).coerceIn(0.0, 1.0)
                val s: Double = if (p <= 0.85) 1.0 - p else 0.15 * Math.pow((1.0 - p) / 0.15, 2.0)
                val q = 1.0 - s
                camX = cd.first + (e.first - cd.first) * q
                camY = cd.second + (e.second - cd.second) * q
                camZ = cd.third + (e.third - cd.third) * q
                val d0 = sqrt(cd.first * cd.first + cd.second * cd.second + cd.third * cd.third)
                curSpeed = d0 / (span / 1000.0) * (if (p <= 0.85) 1.0 else 2.0 * (1.0 - p) / 0.15)
                if (s <= 0.004) {
                    curSpeed = 0.0
                    arrivalName = "Earth"
                    arrivalConst = "Home"
                    pauseUntil = journeyEnd
                }
            } else if (now < pauseUntil) {
                // gentle drift while parked, except at home where we hold still
                if (arrivalName == "Earth") {
                    curSpeed = 0.0
                } else {
                    curSpeed = 0.0008
                    camZ += curSpeed * dt
                }
            } else if (wpIndex < waypoints.size) {
                val wp = waypoints[wpIndex]
                if (!manualLook()) { lookTX = wp.x; lookTY = wp.y; lookTZ = wp.z }
                val dx = wp.x - camX
                val dy = wp.y - camY
                val dz = wp.z - camZ
                val dist = sqrt(dx * dx + dy * dy + dz * dz)
                val arriveDist = if (wp.name == "Earth") 0.05 else 0.2
                if (dist < arriveDist) {
                    arrivalName = wp.name
                    arrivalConst = wp.constellation
                    if (wp.name == "Earth") {
                        pauseUntil = if (journeyEnd > now) journeyEnd else now + 16_000L
                        wpIndex++
                    } else {
                        pauseUntil = now + pauseMs
                        wpIndex++
                    }
                } else {
                    val remaining = (if (now < pauseUntil) 0 else legTravelMs).coerceAtLeast(5_000L)
                    curSpeed = (dist / (remaining / 1000.0)).coerceIn(0.002, 60.0)
                    camX += dx / dist * curSpeed * dt
                    camY += dy / dist * curSpeed * dt
                    camZ += dz / dist * curSpeed * dt
                }
            } else if (homeStage == 0) {
                homeStage = 1
                yaw180 = true
                pauseUntil = if (journeyEnd > now) journeyEnd - 20 * 60_000L else now + 12_000L
            } else {
                curSpeed = 0.002
                camZ += curSpeed * dt
            }
        }

        canvas.drawColor(Color.TRANSPARENT)

        val cx = width / 2f
        val cy = height / 2f
        val focal = minOf(width, height) * 0.9f

        // camera basis: smoothly turn forward toward the look target
        applyLookOffset()
        var tl = sqrt(lookTX * lookTX + lookTY * lookTY + lookTZ * lookTZ)
        if (tl < 1e-6) { lookTX = fX; lookTY = fY; lookTZ = fZ; tl = 1.0 }
        val k = (dt / 8.0).coerceIn(0.0, 1.0)
        var fx2 = fX + (lookTX / tl - fX) * k
        var fy2 = fY + (lookTY / tl - fY) * k
        var fz2 = fZ + (lookTZ / tl - fZ) * k
        var fl = sqrt(fx2 * fx2 + fy2 * fy2 + fz2 * fz2)
        if (fl < 1e-6) { fx2 = 0.0; fy2 = 0.0; fz2 = 1.0; fl = 1.0 }
        fX = fx2 / fl; fY = fy2 / fl; fZ = fz2 / fl
        // right = f x worldUp(0,0,1); if parallel use (1,0,0)
        var crx = fY * 1.0 - fZ * 0.0
        var cry = fZ * 0.0 - fX * 1.0
        var crz = fX * 0.0 - fY * 0.0
        var crl = sqrt(crx * crx + cry * cry + crz * crz)
        if (crl < 1e-6) { crx = 1.0; cry = 0.0; crz = 0.0; crl = 1.0 }
        rX = crx / crl; rY = cry / crl; rZ = crz / crl
        // up = r x f
        uX = rY * fZ - rZ * fY
        uY = rZ * fX - rX * fZ
        uZ = rX * fY - rY * fX
        // gentle roll around forward
        val roll = Math.toRadians(sin(elapsed * 0.04) * 2.5)
        val cosR = kotlin.math.cos(roll)
        val sinR = sin(roll)
        val rX2 = rX * cosR + uX * sinR
        val rY2 = rY * cosR + uY * sinR
        val rZ2 = rZ * cosR + uZ * sinR
        val uX2 = uX * cosR - rX * sinR
        val uY2 = uY * cosR - rY * sinR
        val uZ2 = uZ * cosR - rZ * sinR
        rX = rX2; rY = rY2; rZ = rZ2
        uX = uX2; uY = uY2; uZ = uZ2

        if (alignMode == "window" && alignWindows.isNotEmpty()) {
            for (w in alignWindows) drawWindow(canvas, w)
        } else {
            drawUniverse(canvas, cx, cy, focal, fX, fY, fZ, rX, rY, rZ, uX, uY, uZ, 7.0)
        }

        if (alignPattern) {
            val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; style = Paint.Style.STROKE; strokeWidth = 6f }
            canvas.drawRect(24f, 24f, width - 24f, height - 24f, p)
            p.strokeWidth = 2f
            for (i in 1..7) {
                canvas.drawLine(width * i / 8f, 24f, width * i / 8f, height - 24f, p)
                canvas.drawLine(24f, height * i / 8f, width - 24f, height * i / 8f, p)
            }
            p.style = Paint.Style.FILL
            p.color = Color.rgb(60, 255, 60)
            val cr = 22f
            listOf(24f to 24f, width - 24f to 24f, width - 24f to height - 24f, 24f to height - 24f).forEach {
                canvas.drawCircle(it.first, it.second, cr, p)
            }
            p.color = Color.WHITE
            p.textSize = 40f
            p.textAlign = Paint.Align.CENTER
            canvas.drawText("ALIGN PATTERN", cx, height / 2f, p)
        }

        if (running) drawCrosshair(canvas, cx, cy, focal)

        if (running && now - lastTileFetch > 2000) {
            lastTileFetch = now
            if (starStore == null) {
                try {
                    starStore = StarStore(context, institute.castalia.atlas.player.Settings.atlasStarUrl(context))
                    android.util.Log.d("StarField3D", "star store created for ${institute.castalia.atlas.player.Settings.atlasStarUrl(context)}")
                } catch (e: Exception) {
                    android.util.Log.w("StarField3D", "star store: ${e.message}")
                }
            }
            fetchNeighborhood(now)
        }
        if (remoteStars.isNotEmpty()) drawRemoteStars(canvas, cx, cy, focal, fX, fY, fZ, rX, rY, rZ, uX, uY, uZ)

        if (running) postInvalidateDelayed(33)
    }

    fun setConsLines(on: Boolean) {
        showLines = on
        postInvalidate()
    }

    fun setConsArt(on: Boolean) {
        showArt = on
        postInvalidate()
    }

    fun lookAtStar(name: String): Boolean {
        val l = labels.firstOrNull { it.name.equals(name, ignoreCase = true) } ?: return false
        return lookAtPos(l.x, l.y, l.z)
    }

    fun lookAtCons(name: String): Boolean {
        val fig = consFigs.firstOrNull { it.name.equals(name, ignoreCase = true) } ?: return false
        var sx = 0.0; var sy = 0.0; var sz = 0.0
        var i = 0
        var n = 0
        while (i + 3 <= fig.segs.size) { sx += fig.segs[i]; sy += fig.segs[i + 1]; sz += fig.segs[i + 2]; i += 3; n++ }
        if (n == 0) return false
        return lookAtPos(sx / n, sy / n, sz / n)
    }

    fun clearLook() {
        manualLookUntil = 0L
        lookYaw = 0.0
        lookPitch = 0.0
    }

    /** Manual look-around offsets (degrees), composed onto the journey gaze. */
    fun setLookOffset(yawDeg: Double, pitchDeg: Double) {
        lookYaw = yawDeg.coerceIn(-180.0, 180.0)
        lookPitch = pitchDeg.coerceIn(-85.0, 85.0)
        manualLookUntil = System.currentTimeMillis() + 120_000L
    }

    private fun applyLookOffset() {
        if (!manualLook() || (lookYaw == 0.0 && lookPitch == 0.0)) return
        var lx = lookTX; var ly = lookTY; var lz = lookTZ
        val l = sqrt(lx * lx + ly * ly + lz * lz)
        if (l < 1e-9) return
        lx /= l; ly /= l; lz /= l
        if (lookYaw != 0.0) {
            val a = Math.toRadians(lookYaw)
            val c = kotlin.math.cos(a); val s = sin(a)
            val nx = lx * c - ly * s
            val ny = lx * s + ly * c
            lx = nx; ly = ny
        }
        if (lookPitch != 0.0) {
            val a = Math.toRadians(lookPitch)
            val c = kotlin.math.cos(a); val s = sin(a)
            val rx = rX; val ry = rY; val rz = rZ
            val dot = lx * rx + ly * ry + lz * rz
            val cx = ry * lz - rz * ly
            val cy = rz * lx - rx * lz
            val cz = rx * ly - ry * lx
            lx = lx * c + cx * s + rx * dot * (1 - c)
            ly = ly * c + cy * s + ry * dot * (1 - c)
            lz = lz * c + cz * s + rz * dot * (1 - c)
        }
        lookTX = lx; lookTY = ly; lookTZ = lz
    }

    private fun lookAtPos(x: Double, y: Double, z: Double): Boolean {
        val dx = x - camX
        val dy = y - camY
        val dz = z - camZ
        val d = sqrt(dx * dx + dy * dy + dz * dz)
        if (d < 1e-9) return false
        lookTX = dx; lookTY = dy; lookTZ = dz
        manualLookUntil = System.currentTimeMillis() + 120_000L
        return true
    }

    private fun manualLook(): Boolean = System.currentTimeMillis() < manualLookUntil

    // ----- Atlas streaming catalog -----
    private var starStore: StarStore? = null
    private var lastTileFetch = 0L
    private var lastTileHits = 0
    private val remoteByCell = HashMap<Long, FloatArray>()
    private var remoteStars = FloatArray(0)
    private var remoteDirty = false

    private fun fetchNeighborhood(now: Long) {
        val store = starStore ?: return
        val camR = sqrt(camX * camX + camY * camY + camZ * camZ)
        val lvl = (2 + Math.log(Math.max(1.0, camR / 16.0) + 1e-9) / Math.log(2.0)).toInt()
            .coerceIn(2, 11)
        val n = (1 shl StarStore.OCT_DEPTH) - 1
        val cx = (((camX + StarStore.PC_BOX) / (2 * StarStore.PC_BOX)) * (1 shl StarStore.OCT_DEPTH)).toInt().coerceIn(0, n)
        val cy = (((camY + StarStore.PC_BOX) / (2 * StarStore.PC_BOX)) * (1 shl StarStore.OCT_DEPTH)).toInt().coerceIn(0, n)
        val cz = (((camZ + StarStore.PC_BOX) / (2 * StarStore.PC_BOX)) * (1 shl StarStore.OCT_DEPTH)).toInt().coerceIn(0, n)
        val wanted = ArrayList<Pair<Long, Long>>(27)
        for (dx in -1..1) for (dy in -1..1) for (dz in -1..1) {
            val x = (cx + dx).coerceIn(0, n)
            val y = (cy + dy).coerceIn(0, n)
            val z = (cz + dz).coerceIn(0, n)
            wanted.add(Pair(StarStore.cellKey(
                (-StarStore.PC_BOX + x * StarStore.CELL_EDGE) + 1.0,
                (-StarStore.PC_BOX + y * StarStore.CELL_EDGE) + 1.0,
                (-StarStore.PC_BOX + z * StarStore.CELL_EDGE) + 1.0), 0L))
        }
        var changed = false
        for ((k, _) in wanted) {
            val key = "space/L$lvl/$k"
            if (!remoteByCell.containsKey(k) && store.get(key) == null) {
                store.request(key, 0)
            }
            val before = store.tileHits
            val b = store.get(key)
            if (b != null && !remoteByCell.containsKey(k)) {
                remoteByCell[k] = decodeTile(b, k)
                changed = true
            }
        }
        if (changed) {
            rebuildRemote()
            postInvalidate()
        }
    }

    private fun decodeTile(bytes: ByteArray, cellKey: Long): FloatArray {
        val decoded = StarStore.decode3D(bytes)
        val n = decoded[0].size
        val out = FloatArray(n * 5)
        // recover cell from the absolute center we used when requesting
        val xBits = (cellKey and 0x5555555555555555L.inv() shr 1) // unused; compute from stored center
        val n_ = (1 shl StarStore.OCT_DEPTH) - 1
        // decode absolute coords: we know the tile by key; invert morton
        fun gather(v: Long): Int {
            var r = 0
            for (b in 0 until 8) {
                r = r or (((v shr (b * 3)).toInt() and 1) shl b)
            }
            return r
        }
        val gx = gather(cellKey)
        val gy = gather(cellKey shr 1)
        val gz = gather(cellKey shr 2)
        val loX = -StarStore.PC_BOX + gx * StarStore.CELL_EDGE
        val loY = -StarStore.PC_BOX + gy * StarStore.CELL_EDGE
        val loZ = -StarStore.PC_BOX + gz * StarStore.CELL_EDGE
        for (i in 0 until n) {
            out[i * 5] = (loX + decoded[0][i] * StarStore.CELL_EDGE).toFloat()
            out[i * 5 + 1] = (loY + decoded[1][i] * StarStore.CELL_EDGE).toFloat()
            out[i * 5 + 2] = (loZ + decoded[2][i] * StarStore.CELL_EDGE).toFloat()
            out[i * 5 + 3] = decoded[3][i]
            out[i * 5 + 4] = decoded[4][i]
        }
        return out
    }

    private fun rebuildRemote() {
        var total = 0
        for (v in remoteByCell.values) total += v.size
        val out = FloatArray(total)
        var o = 0
        for (v in remoteByCell.values) {
            System.arraycopy(v, 0, out, o, v.size)
            o += v.size
        }
        remoteStars = out
    }

    fun skyObjects(): org.json.JSONObject {
        val cons = org.json.JSONArray()
        for (f in consFigs.map { it.name }.sorted()) cons.put(f)
        val stars = org.json.JSONArray()
        for (s in labels.map { it.name }.distinct().sorted()) stars.put(s)
        return org.json.JSONObject().put("stars", stars).put("constellations", cons)
    }

    private fun drawMilkyWay(
        canvas: Canvas, cx: Float, cy: Float, focal: Float,
        fX: Double, fY: Double, fZ: Double,
        rX: Double, rY: Double, rZ: Double,
        uX: Double, uY: Double, uZ: Double
    ) {
        val segs = bandSegs ?: return
        bandPaint.style = Paint.Style.STROKE
        for (pass in 0 until 2) {
            var i = 0
            while (i + 10 <= segs.size) {
                val w = segs[i + 6]
                if (w >= 0.02) {
                    val sz1 = segs[i] * fX + segs[i + 1] * fY + segs[i + 2] * fZ
                    val sz2 = segs[i + 3] * fX + segs[i + 4] * fY + segs[i + 5] * fZ
                    if (sz1 >= 0.05 && sz2 >= 0.05) {
                        val sx1 = segs[i] * rX + segs[i + 1] * rY + segs[i + 2] * rZ
                        val sy1 = segs[i] * uX + segs[i + 1] * uY + segs[i + 2] * uZ
                        val sx2 = segs[i + 3] * rX + segs[i + 4] * rY + segs[i + 5] * rZ
                        val sy2 = segs[i + 3] * uX + segs[i + 4] * uY + segs[i + 5] * uZ
                        bandPaint.color = Color.rgb(
                            (segs[i + 7] * 255.0).toInt().coerceIn(0, 255),
                            (segs[i + 8] * 255.0).toInt().coerceIn(0, 255),
                            (segs[i + 9] * 255.0).toInt().coerceIn(0, 255)
                        )
                        if (pass == 0) {
                            bandPaint.strokeWidth = (6.0f + 40.0f * w.toFloat()) * density
                            bandPaint.alpha = (36 * w).toInt().coerceIn(0, 255)
                        } else {
                            bandPaint.strokeWidth = (2.0f + 9.0f * w.toFloat()) * density
                            bandPaint.alpha = (130 * w).toInt().coerceIn(0, 255)
                        }
                        canvas.drawLine(
                            (cx + focal * sx1 / sz1).toFloat(),
                            (cy - focal * sy1 / sz1).toFloat(),
                            (cx + focal * sx2 / sz2).toFloat(),
                            (cy - focal * sy2 / sz2).toFloat(),
                            bandPaint
                        )
                    }
                }
                i += 10
            }
        }
    }

    private fun buildBand(): FloatArray {
        val bmp = mwBmp ?: return FloatArray(0)
        val bw = bmp.width
        val bh = bmp.height
        val px = IntArray(bw * bh)
        bmp.getPixels(px, 0, bw, 0, 0, bw, bh)
        val out = ArrayList<Float>(4096)
        val dg = Math.toRadians(27.12825)
        val ag = Math.toRadians(192.85948)
        val lncp = Math.toRadians(122.93192)
        var prev: DoubleArray? = null
        val rings = doubleArrayOf(-14.0, -10.5, -7.0, -3.5, 0.0, 3.5, 7.0, 10.5, 14.0)
        for (b in rings) {
            prev = null
            val bR = Math.toRadians(b)
            val sb = sin(bR)
            val cb = kotlin.math.cos(bR)
            for (li in 0..180) {
                val l = Math.toRadians(li * 2.0)
                val dl = lncp - l
                val sinDec = sin(dg) * sb + kotlin.math.cos(dg) * cb * kotlin.math.cos(dl)
                val dec = kotlin.math.asin(sinDec.coerceIn(-1.0, 1.0))
                var ra = ag + Math.atan2(
                    cb * sin(dl),
                    kotlin.math.cos(dg) * sb - sin(dg) * cb * kotlin.math.cos(dl)
                )
                if (ra < 0) ra += 2.0 * Math.PI
                if (ra >= 2.0 * Math.PI) ra -= 2.0 * Math.PI
                val uu = ((ra / (2.0 * Math.PI)) * bw).toInt().coerceIn(0, bw - 1)
                val vv = ((0.5 - dec / Math.PI) * bh).toInt().coerceIn(0, bh - 1)
                val argb = px[vv * bw + uu]
                val a = (argb ushr 24) / 255.0
                val cr = ((argb shr 16) and 0xff) / 255.0
                val cg = ((argb shr 8) and 0xff) / 255.0
                val cbl = (argb and 0xff) / 255.0
                val w = Math.pow(a, 1.5)
                val dir = doubleArrayOf(
                    kotlin.math.cos(dec) * kotlin.math.cos(ra),
                    kotlin.math.cos(dec) * sin(ra),
                    sin(dec)
                )
                val p = prev
                if (p != null) {
                    val wAvg = (w + p[3]) / 2.0
                    if (wAvg >= 0.02) {
                        out.add(p[0].toFloat()); out.add(p[1].toFloat()); out.add(p[2].toFloat())
                        out.add(dir[0].toFloat()); out.add(dir[1].toFloat()); out.add(dir[2].toFloat())
                        out.add(wAvg.toFloat())
                        out.add(((cr + p[4]) / 2.0).toFloat())
                        out.add(((cg + p[5]) / 2.0).toFloat())
                        out.add(((cbl + p[6]) / 2.0).toFloat())
                    }
                }
                prev = doubleArrayOf(dir[0], dir[1], dir[2], w, cr, cg, cbl)
            }
        }
        return out.toFiniteFloatArray()
    }

    private fun ArrayList<Float>.toFiniteFloatArray(): FloatArray {
        val arr = FloatArray(size)
        for (i in 0 until size) arr[i] = this[i]
        return arr
    }

    private fun drawConsLines(
        canvas: Canvas, cx: Float, cy: Float, focal: Float,
        fX: Double, fY: Double, fZ: Double,
        rX: Double, rY: Double, rZ: Double,
        uX: Double, uY: Double, uZ: Double
    ) {
        for (fig in consFigs) {
            val s = fig.segs
            var i = 0
            while (i + 6 <= s.size) {
                val vx1 = s[i] - camX
                val vy1 = s[i + 1] - camY
                val vz1 = s[i + 2] - camZ
                val vx2 = s[i + 3] - camX
                val vy2 = s[i + 4] - camY
                val vz2 = s[i + 5] - camZ
                val sz1 = vx1 * fX + vy1 * fY + vz1 * fZ
                val sz2 = vx2 * fX + vy2 * fY + vz2 * fZ
                if (sz1 >= 0.05 && sz2 >= 0.05) {
                    val px1 = cx + (focal * (vx1 * rX + vy1 * rY + vz1 * rZ) / sz1).toFloat()
                    val py1 = cy - (focal * (vx1 * uX + vy1 * uY + vz1 * uZ) / sz1).toFloat()
                    val px2 = cx + (focal * (vx2 * rX + vy2 * rY + vz2 * rZ) / sz2).toFloat()
                    val py2 = cy - (focal * (vx2 * uX + vy2 * uY + vz2 * uZ) / sz2).toFloat()
                    canvas.drawLine(px1, py1, px2, py2, linePaint)
                }
                i += 6
            }
        }
    }

    private fun drawArt3D(
        canvas: Canvas, cx: Float, cy: Float, focal: Float,
        fX: Double, fY: Double, fZ: Double,
        rX: Double, rY: Double, rZ: Double,
        uX: Double, uY: Double, uZ: Double
    ) {
        for (a in artFigs) {
            val pts = a.pts
            val nAnchors = pts.size / 4
            if (nAnchors < 2) continue
            var n = 0
            val src = FloatArray(8)
            val dst = FloatArray(8)
            for (k in 0 until nAnchors) {
                if (n >= 4) break
                val raR = Math.toRadians(pts[k * 4].toDouble())
                val decR = Math.toRadians(pts[k * 4 + 1].toDouble())
                val wx = kotlin.math.cos(decR) * kotlin.math.cos(raR)
                val wy = kotlin.math.cos(decR) * sin(raR)
                val wz = sin(decR)
                val sz = wx * fX + wy * fY + wz * fZ
                if (sz < 0.12) continue
                src[n * 2] = pts[k * 4 + 2]
                src[n * 2 + 1] = pts[k * 4 + 3]
                dst[n * 2] = (cx + focal * (wx * rX + wy * rY + wz * rZ) / sz).toFloat()
                dst[n * 2 + 1] = (cy - focal * (wx * uX + wy * uY + wz * uZ) / sz).toFloat()
                n++
            }
            if (n < 2) continue
            val m = Matrix()
            val order = if (n >= 3) intArrayOf(minOf(n, 4), 3, 2) else intArrayOf(2)
            var ok = false
            for (cnt in order) {
                ok = try {
                    m.setPolyToPoly(src, 0, dst, 0, cnt)
                } catch (e: Exception) {
                    false
                }
                if (ok) break
            }
            if (!ok) continue
            val bmp = artBitmap(a.image) ?: continue
            artPaint3D.alpha = 190
            canvas.drawBitmap(bmp, m, artPaint3D)
        }
    }

    private fun artBitmap(image: String): android.graphics.Bitmap? {
        artBmpCache[image]?.let { return it }
        return try {
            val opts = android.graphics.BitmapFactory.Options().apply {
                inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
            }
            context.assets.open("sky/art/$image").use {
                android.graphics.BitmapFactory.decodeStream(it, null, opts)
            }?.let {
                artBmpCache[image] = it
                it
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun drawUniverse(
        canvas: Canvas, cx: Float, cy: Float, focal: Float,
        fX: Double, fY: Double, fZ: Double,
        rX: Double, rY: Double, rZ: Double,
        uX: Double, uY: Double, uZ: Double,
        magCut: Double
    ) {
        val W = canvas.width
        val H = canvas.height
                if (mwBmp != null) {
            drawMilkyWay(canvas, cx, cy, focal, fX, fY, fZ, rX, rY, rZ, uX, uY, uZ)
        }
        if (showArt) {
            drawArt3D(canvas, cx, cy, focal, fX, fY, fZ, rX, rY, rZ, uX, uY, uZ)
        }
        if (showLines) {
            drawConsLines(canvas, cx, cy, focal, fX, fY, fZ, rX, rY, rZ, uX, uY, uZ)
        }
        for (b in 0 until 16) dimCount[b] = 0
        for (st in stars) {
            val vx = st.x - camX
            val vy = st.y - camY
            val vz = st.z - camZ
            val d2 = vx * vx + vy * vy + vz * vz
            if (d2 > if (magCut >= 7.0) st.r70Sq else st.r65Sq) continue
            val sz = vx * fX + vy * fY + vz * fZ
            if (sz < 0.05) continue
            val dist = sqrt(d2)
            val mApp = st.absM + 5 * (Math.log10(dist.coerceAtLeast(1e-6)) - 1)
            if (mApp > magCut) continue
            val sx = vx * rX + vy * rY + vz * rZ
            val sy = vx * uX + vy * uY + vz * uZ
            val px = cx + (focal * sx / sz).toFloat()
            val py = cy - (focal * sy / sz).toFloat()
            if (px < -20 || px > W + 20 || py < -20 || py > H + 20) continue
            val t = (7.0 - mApp).coerceIn(0.0, 9.0)
            val alpha = (((t / 7.0) * 0.85 + 0.15) * 255).toInt().coerceIn(40, 255)
            if (mApp < 1.8) {
                starPaint.color = starColor(st.ci)
                starPaint.alpha = alpha
                canvas.drawCircle(px, py, 2.0f * density, starPaint)
            } else {
                val classIdx = when {
                    st.ci < -0.15 -> 0
                    st.ci < 0.15 -> 1
                    st.ci < 0.45 -> 2
                    st.ci < 0.70 -> 3
                    st.ci < 1.10 -> 4
                    st.ci < 1.65 -> 5
                    st.ci < 2.25 -> 6
                    else -> 7
                }
                val sizeIdx = if (mApp < 4.5) 0 else 1
                val bucket = classIdx * 2 + sizeIdx
                if (dimCount[bucket] < 6000) {
                    dimBuckets[bucket][dimCount[bucket] * 2] = px
                    dimBuckets[bucket][dimCount[bucket] * 2 + 1] = py
                    dimCount[bucket]++
                }
            }
        }
        for (b in 0 until 16) {
            dimPaints[b].alpha = if (b % 2 == 0) 230 else 170
            canvas.drawPoints(dimBuckets[b], 0, dimCount[b] * 2, dimPaints[b])
        }
        val camHome = sqrt(camX * camX + camY * camY + camZ * camZ) < 1.0
        for (p in planets) {
            if (!camHome) break
            val pos = planetPos[p.name] ?: continue
            val vx = pos.first - camX
            val vy = pos.second - camY
            val vz = pos.third - camZ
            val dist = sqrt(vx * vx + vy * vy + vz * vz)
            if (dist < 0.05) continue  // inside/next to the billboard: skip to avoid full-screen texture
            val sz = vx * fX + vy * fY + vz * fZ
            if (sz < 0.05) continue
            val sx = vx * rX + vy * rY + vz * rZ
            val sy = vx * uX + vy * uY + vz * uZ
            val screenX = cx + (focal * sx / sz).toFloat()
            val screenY = cy - (focal * sy / sz).toFloat()
            val rzF = sz.toFloat().coerceIn(0.12f, 6f)
            val bigCap = minOf(W, H) * (if (p.name == "Earth") 0.44f else 0.30f)
            // true-proportional angular size: (R_km / d_km) × focal × gain
            val dKm = dist * 3.086e13
            val rPx = ((p.radiusKm / dKm) * focal * SIZE_GAIN).toFloat().coerceIn(3f, bigCap)
            if (rPx >= bigCap * 0.75f) continue  // camera in the billboard: skip
            if (screenX < -rPx - 40 || screenX > W + rPx + 40 || screenY < -rPx - 40 || screenY > H + rPx + 40) continue
            drawPlanet(canvas, screenX, screenY, rPx, p)
        }
    }

    private fun drawCrosshair(canvas: Canvas, cx: Float, cy: Float, focal: Float) {
        if (alignMode == "window") return
        val thr = minOf(width, height) * 0.13f
        val thrSq = (thr * thr).toDouble()
        var bestSq = Double.MAX_VALUE
        var bx = 0f
        var by = 0f
        var bn: String? = null
        val home = sqrt(camX * camX + camY * camY + camZ * camZ) < 1.0
        fun consider(nm: String, wx: Double, wy: Double, wz: Double) {
            val vx = wx - camX
            val vy = wy - camY
            val vz = wz - camZ
            val sz = vx * fX + vy * fY + vz * fZ
            if (sz < 0.05) return
            val sx = vx * rX + vy * rY + vz * rZ
            val sy = vx * uX + vy * uY + vz * uZ
            val px = cx + (focal * sx / sz).toFloat()
            val py = cy - (focal * sy / sz).toFloat()
            val d2 = (px - cx).toDouble() * (px - cx) + (py - cy).toDouble() * (py - cy)
            if (d2 < bestSq) {
                bestSq = d2
                bx = px
                by = py
                bn = nm
            }
        }
        for (l in labels) {
            val dvx = l.x - camX
            val dvy = l.y - camY
            val dvz = l.z - camZ
            if (dvx * dvx + dvy * dvy + dvz * dvz < 36.0) consider(l.name, l.x, l.y, l.z)
        }
        destWp?.let { consider(if (it.name.isBlank()) "STAR" else it.name, it.x, it.y, it.z) }
        if (home) for (p in planets) planetPos[p.name]?.let { consider(p.name, it.first, it.second, it.third) }
        if (bn == null || bestSq > thrSq) return
        val nm = bn ?: return
        val cr = 12f * density
        canvas.drawLine(bx - cr, by, bx - cr * 0.4f, by, crossPaint)
        canvas.drawLine(bx + cr * 0.4f, by, bx + cr, by, crossPaint)
        canvas.drawLine(bx, by - cr, bx, by - cr * 0.4f, crossPaint)
        canvas.drawLine(bx, by + cr * 0.4f, bx, by + cr, crossPaint)
        labelPaint.alpha = 235
        canvas.drawText(nm, bx, by - cr - 5f * density, labelPaint)
        labelPaint.alpha = 204
    }

        private fun drawRemoteStars(
        canvas: Canvas, cx: Float, cy: Float, focal: Float,
        fX: Double, fY: Double, fZ: Double,
        rX: Double, rY: Double, rZ: Double,
        uX: Double, uY: Double, uZ: Double
    ) {
        val rs = remoteStars
        val W = canvas.width
        val H = canvas.height
        var i = 0
        while (i + 5 <= rs.size) {
            val vx = rs[i] - camX
            val vy = rs[i + 1] - camY
            val vz = rs[i + 2] - camZ
            val sz = vx * fX + vy * fY + vz * fZ
            if (sz >= 0.05) {
                val dist = sqrt(vx * vx + vy * vy + vz * vz)
                val mApp = rs[i + 3] + 5 * (Math.log10(dist.coerceAtLeast(1e-6)) - 1)
                if (mApp < 9.0) {
                    val px = cx + (focal * (vx * rX + vy * rY + vz * rZ) / sz).toFloat()
                    val py = cy - (focal * (vx * uX + vy * uY + vz * uZ) / sz).toFloat()
                    if (px >= -20 && px <= W + 20 && py >= -20 && py <= H + 20) {
                        val t = (7.0 - mApp).coerceIn(0.0, 9.0)
                        val alpha = (((t / 7.0) * 0.85 + 0.15) * 255).toInt().coerceIn(40, 255)
                        starPaint.color = starColor(rs[i + 4].toDouble())
                        starPaint.alpha = alpha
                        canvas.drawPoint(px, py, starPaint)
                    }
                }
            }
            i += 5
        }
    }

    fun telemetryJson(): org.json.JSONObject {
        val dec = Math.toDegrees(kotlin.math.asin(fZ.coerceIn(-1.0, 1.0)))
        val ra = (Math.toDegrees(Math.atan2(fY, fX)) + 360.0) % 360.0
        val now = System.currentTimeMillis()
        val atTarget = running && now < pauseUntil && arrivalName != null
        val dest = destWp
        val warp = Math.pow((curSpeed * 1.0295e8).coerceAtLeast(0.0), 0.3)
        val cal = Calendar.getInstance()
        val clock = "%02d:%02d:%02d".format(
            cal.get(Calendar.HOUR_OF_DAY), cal.get(Calendar.MINUTE), cal.get(Calendar.SECOND)
        )
        return org.json.JSONObject()
            .put("clock", clock)
            .put("lookYaw", lookYaw)
            .put("lookPitch", lookPitch)
            .put("running", running)
            .put("starsLoaded", stars.size)
            .put("timeScale", timeScale.toDouble())
            .put("posX", camX * 3.26156)
            .put("posY", camY * 3.26156)
            .put("posZ", camZ * 3.26156)
            .put("speedC", curSpeed)
            .put("warp", warp)
            .put("headingRa", ra)
            .put("headingDec", dec)
            .put(
                "heading",
                if (atTarget && arrivalName != null) "\u2192 ${arrivalName}" else "RA %.1f\u00b0 DEC %+.1f\u00b0".format(ra, dec)
            )
            .put("targetName", arrivalName)
            .put("targetConst", arrivalConst)
            .put("destName", dest?.name)
            .put("destConst", dest?.constellation)
            .put("destDistLy", dest?.let { sqrt(it.x * it.x + it.y * it.y + it.z * it.z) * 3.26156 } ?: 0.0)
            .put("homeStage", homeStage)
            .put("wpIndex", wpIndex)
            .put("wpCount", waypoints.size)
            .put("outboundStartMs", outboundStart)
            .put("returnStartMs", returnStart)
            .put("journeyEndMs", journeyEnd)
    }

    fun alignJson(): org.json.JSONObject = org.json.JSONObject()
        .put("mode", alignMode)
        .put("pattern", alignPattern)
        .put(
            "windows",
            org.json.JSONArray().apply {
                alignWindows.forEach { w ->
                    put(
                        org.json.JSONObject()
                            .put("dir", w.dir)
                            .put("quad", org.json.JSONArray(w.quad.toList()))
                    )
                }
            }
        )

    private fun windowBasis(dir: String): Triple<Double, Double, Double> {
        // directions relative to the current travel heading
        val zw = 0.0; var ux = 0.0; var uy = 0.0; var uz = 1.0
        return when (dir.uppercase()) {
            "B" -> Triple(-fX, -fY, -fZ)
            "L", "R" -> {
                // horizontal side: f x worldUp
                var sx = fY * 1.0 - fZ * 0.0
                var sy = fZ * 0.0 - fX * 1.0
                var sz2 = fX * 0.0 - fY * 0.0
                var sl = sqrt(sx * sx + sy * sy + sz2 * sz2)
                if (sl < 1e-6) { sx = 1.0; sy = 0.0; sz2 = 0.0; sl = 1.0 }
                if (dir.uppercase() == "L") { sx = -sx; sy = -sy; sz2 = -sz2 }
                Triple(sx / sl, sy / sl, sz2 / sl)
            }
            "U" -> {
                // world up projected perpendicular to f
                val dot = uz * fZ
                var px2 = ux - fX * dot
                var py2 = uy - fY * dot
                var pz2 = uz - fZ * dot
                val pl = sqrt(px2 * px2 + py2 * py2 + pz2 * pz2)
                if (pl < 1e-6) Triple(-fX, -fY, -fZ) else Triple(px2 / pl, py2 / pl, pz2 / pl)
            }
            else -> Triple(fX, fY, fZ)
        }
    }

    private fun drawWindow(canvas: Canvas, w: SkyWindow) {
        val q = w.quad
        val xs = floatArrayOf(q[0], q[2], q[4], q[6]).map { it * canvas.width }
        val ys = floatArrayOf(q[1], q[3], q[5], q[7]).map { it * canvas.height }
        val left = xs.min(); val right = xs.max()
        val top = ys.min(); val bot = ys.max()
        val wPx = (right - left).toInt().coerceIn(80, canvas.width)
        val hPx = (bot - top).toInt().coerceIn(60, canvas.height)
        var bmp = windowBmps[w]
        if (bmp == null || bmp.width != wPx || bmp.height != hPx) {
            if (bmp != null) bmp.recycle()
            bmp = android.graphics.Bitmap.createBitmap(wPx, hPx, android.graphics.Bitmap.Config.ARGB_8888)
            windowBmps[w] = bmp
        }
        val b = bmp!!
        b.eraseColor(Color.TRANSPARENT)
        val wf = windowBasis(w.dir)
        val f = Triple(wf.first, wf.second, wf.third)
        // right = f x worldUp
        var sx = f.second; var sy = -f.first; var sz2 = 0.0
        var sl = sqrt(sx * sx + sy * sy + sz2 * sz2)
        if (sl < 1e-6) { sx = 1.0; sy = 0.0; sl = 1.0 }
        val r = Triple(sx / sl, sy / sl, sz2 / sl)
        val u = Triple(
            r.second * f.third - r.third * f.second,
            r.third * f.first - r.first * f.third,
            r.first * f.second - r.second * f.first
        )
        drawUniverse(
            Canvas(b), wPx / 2f, hPx / 2f,
            minOf(canvas.width, canvas.height) * 0.9f,
            f.first, f.second, f.third,
            r.first, r.second, r.third,
            u.first, u.second, u.third,
            6.5
        )
        drawQuadWarp(canvas, b, xs.toFloatArray(), ys.toFloatArray())
    }

    private fun drawQuadWarp(canvas: Canvas, bmp: android.graphics.Bitmap, xs: FloatArray, ys: FloatArray) {
        // quad: TL, TR, BR, BL — two affine triangles with clip
        val w = bmp.width.toFloat()
        val h = bmp.height.toFloat()
        for (t in 0..1) {
            val path = android.graphics.Path()
            if (t == 0) {
                path.moveTo(xs[0], ys[0]); path.lineTo(xs[1], ys[1]); path.lineTo(xs[2], ys[2])
            } else {
                path.moveTo(xs[0], ys[0]); path.lineTo(xs[2], ys[2]); path.lineTo(xs[3], ys[3])
            }
            path.close()
            val src = floatArrayOf(0f, 0f, w, 0f, w, h)
            val dst = if (t == 0) {
                floatArrayOf(xs[0], ys[0], xs[1], ys[1], xs[2], ys[2])
            } else {
                floatArrayOf(0f, 0f, xs[2] - xs[0], ys[2] - ys[0], xs[3] - xs[0], ys[3] - ys[0])
            }
            val m = android.graphics.Matrix()
            if (t == 0) {
                m.setPolyToPoly(floatArrayOf(0f, 0f, w, 0f, w, h), 0, dst, 0, 3)
            } else {
                m.setPolyToPoly(src, 0, dst, 0, 3)
            }
            canvas.save()
            canvas.clipPath(path)
            canvas.drawBitmap(bmp, m, bmpPaint)
            canvas.restore()
        }
    }

    private fun drawPlanet(canvas: Canvas, x: Float, y: Float, r: Float, p: Planet) {
        val bmp = planetBmp[p.bmp + "_globe"] ?: planetBmp[p.bmp]
        if (bmp == null) {
            starPaint.color = 0xFFEAD9B0.toInt()
            canvas.drawCircle(x, y, r, starPaint)
            return
        }
        val dst = android.graphics.RectF(x - r, y - r, x + r, y + r)
        canvas.drawBitmap(bmp, null, dst, bmpPaint)
        if (p.ring) {
            ringBmp?.let { ring ->
                canvas.save()
                canvas.rotate(-18f, x, y)
                val rw = r * 4.4f
                val rh = r * 1.6f
                canvas.drawBitmap(ring, null, android.graphics.RectF(x - rw, y - rh, x + rw, y + rh), bmpPaint)
                canvas.restore()
            }
        }
    }

    private fun starColor(ci: Double): Int {
        val t = 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))
        val temp = t.coerceIn(1200.0, 40000.0) / 100.0
        val r: Double
        val g: Double
        val b: Double
        if (temp <= 66) {
            r = 255.0
            g = 99.4708025861 * Math.log(temp) - 161.1195681661
        } else {
            r = 329.698727446 * Math.pow(temp - 60, -0.1332047592)
            g = 288.1221695283 * Math.pow(temp - 60, -0.0755148492)
        }
        b = when {
            temp >= 66 -> 255.0
            temp <= 19 -> 0.0
            else -> 138.5177312231 * Math.log(temp - 10) - 305.0447927307
        }
        return Color.rgb(
            ((0.5 + (r / 255.0 - 0.5) * 1.9) * 255).toInt().coerceIn(0, 255),
            ((0.5 + (g / 255.0 - 0.5) * 1.9) * 255).toInt().coerceIn(0, 255),
            ((0.5 + (b / 255.0 - 0.5) * 1.9) * 255).toInt().coerceIn(0, 255)
        )
    }

    companion object {
        private const val MAX_DIM = 4000
        const val TRAVEL_CAP_PC = 2.0
        const val RENDER_MAG = 7.0
        private const val STAY_MS = 20 * 60_000L

        private fun rVisSq(absM: Double, magCut: Double): Double {
            val d = Math.pow(10.0, (magCut - absM) / 5.0 + 1.0)
            return d * d
        }

        // the "father's star" for each nightly featured constellation
        private val FATHER_STAR = mapOf(
            "Cygnus" to "Deneb",
            "Lyra" to "Vega",
            "Ursa Minor" to "Polaris",
            "Ursa Major" to "Alioth",
            "Cassiopeia" to "Schedar",
            "Andromeda" to "Alpheratz",
            "Taurus" to "Aldebaran",
            "Scorpius" to "Antares",
            "Orion" to "Betelgeuse",
            "Pegasus" to "Enif"
        )
    }
}
