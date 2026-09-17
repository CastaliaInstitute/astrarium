package institute.castalia.atlas.player.sky

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
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
        val exagDistPc: Double = 0.1
    )

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

    private val planets = listOf(
        Planet("Earth", "earth", 10f, subtitle = "Home"),
        Planet("Moon", "moon", 9f, subtitle = "Earth's companion", exagDistPc = 0.02),
        Planet("Mars", "mars", 9f, subtitle = "The red planet", exagDistPc = 0.05),
        Planet("Jupiter", "jupiter", 15f, subtitle = "King of planets", exagDistPc = 0.12),
        Planet("Saturn", "saturn", 13f, ring = true, subtitle = "Lord of the rings", exagDistPc = 0.20)
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
            // procedural galaxy population: binary floats parsed off the main thread
            kotlin.concurrent.thread {
                try {
                    val bytes = context.assets.open("sky/galaxy3d.bin").readBytes()
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
                        android.util.Log.d("StarField3D", "galaxy loaded: ${extra.size} synthetic, ${all.size} total")
                        postInvalidate()
                    }
                } catch (e: Exception) {
                }
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

    private val density = resources.displayMetrics.density
    private val starPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG)
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
            waypoints.addAll(planetWps())
            waypoints.addAll(starRoute)
        }
        if (destWp != null && midnight > 0) {
            when {
                now < midnight -> {
                    homeStage = 0
                    yaw180 = false
                    val span = (midnight - outboundStart).coerceAtLeast(60_000L)
                    val p = ((now - outboundStart).toDouble() / span).coerceIn(0.0, 1.0)
                    camX = destWp!!.x * p
                    camY = destWp!!.y * p
                    camZ = destWp!!.z * p
                }
                now < returnStart -> {
                    homeStage = 1
                    yaw180 = true
                    camX = destWp!!.x
                    camY = destWp!!.y
                    camZ = destWp!!.z
                    arrivalName = destWp!!.name
                    arrivalConst = destWp!!.constellation
                    pauseUntil = returnStart
                }
                else -> {
                    homeStage = 2
                    yaw180 = true
                    val span = (journeyEnd - returnStart).coerceAtLeast(60_000L)
                    val p = ((now - returnStart).toDouble() / span).coerceIn(0.0, 1.0)
                    camX = destWp!!.x * (1 - p)
                    camY = destWp!!.y * (1 - p)
                    camZ = destWp!!.z * (1 - p)
                }
            }
        } else {
            val hoursToDawn = journeyEndMs > now + 30 * 60_000L
            legMs = if (hoursToDawn) (journeyEndMs - now - 30 * 60_000L) / (waypoints.size + 1).coerceAtLeast(1) else 0L
            legTravelMs = if (hoursToDawn) (legMs * 0.6).toLong().coerceAtLeast(30_000L) else 45_000L
            pauseMs = if (hoursToDawn) (legMs * 0.4).toLong().coerceAtLeast(60_000L) else 16_000L
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
        if (figStars != null && figStars.isNotEmpty()) {
            var best: Star3D? = null
            var bestD = 0.0
            for ((raDeg, decDeg) in figStars) {
                val ra = Math.toRadians(raDeg)
                val dec = Math.toRadians(decDeg)
                val ux = kotlin.math.cos(dec) * kotlin.math.cos(ra)
                val uy = kotlin.math.cos(dec) * kotlin.math.sin(ra)
                val uz = kotlin.math.sin(dec)
                for (s in stars) {
                    val d = sqrt(s.x * s.x + s.y * s.y + s.z * s.z).coerceAtLeast(1e-9)
                    if (d <= bestD || d > 2000.0) continue
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
                return Wp(named?.name ?: "Farthest star", constellation, it.x, it.y, it.z)
            }
        }
        val starName = FATHER_STAR[constellation] ?: return null
        val l = labels.firstOrNull { it.name == starName } ?: return null
        return Wp(l.name, constellation, l.x, l.y, l.z)
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
                lookTX = -wp.x; lookTY = -wp.y; lookTZ = -wp.z
                arrivalName = wp.name; arrivalConst = wp.constellation
                pauseUntil = Long.MAX_VALUE
            } else if (anchored2 && homeStage == 0) {
                // outbound: pure time function, arriving exactly at midnight
                val wp = destWp!!
                lookTX = wp.x; lookTY = wp.y; lookTZ = wp.z
                val span = (midnight - outboundStart).coerceAtLeast(60_000L)
                val p = ((machineNow - outboundStart).toDouble() / span).coerceIn(0.0, 1.0)
                camX = wp.x * p
                camY = wp.y * p
                camZ = wp.z * p
                curSpeed = sqrt(wp.x * wp.x + wp.y * wp.y + wp.z * wp.z) / (span / 1000.0)
                if (machineNow >= midnight - 2_000L) {
                    camX = wp.x
                    camY = wp.y
                    camZ = wp.z
                    arrivalName = wp.name
                    arrivalConst = wp.constellation
                    homeStage = 1
                    yaw180 = true
                    pauseUntil = returnStart
                }
            } else if (anchored2 && homeStage == 1) {
                val wp = destWp!!
                lookTX = -wp.x; lookTY = -wp.y; lookTZ = -wp.z
                camX = wp.x
                camY = wp.y
                camZ = wp.z
                curSpeed = 0.0
                if (machineNow >= returnStart) {
                    homeStage = 2
                    yaw180 = true
                }
            } else if (anchored2 && homeStage == 2) {
                // return: linear so 3am is just past halfway, easing only at the very end for the Earth approach
                // Earth drifts in the galactic frame while we travel, so we aim at where it will be
                val wp = destWp!!
                val e = earthPos(machineNow)
                lookTX = e.first - camX; lookTY = e.second - camY; lookTZ = e.third - camZ
                val span = (journeyEnd - returnStart).coerceAtLeast(60_000L)
                val p = ((machineNow - returnStart).toDouble() / span).coerceIn(0.0, 1.0)
                val s: Double = if (p <= 0.85) 1.0 - p else 0.15 * Math.pow((1.0 - p) / 0.15, 2.0)
                val q = 1.0 - s
                camX = wp.x + (e.first - wp.x) * q
                camY = wp.y + (e.second - wp.y) * q
                camZ = wp.z + (e.third - wp.z) * q
                val d0 = sqrt(wp.x * wp.x + wp.y * wp.y + wp.z * wp.z)
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
                lookTX = wp.x; lookTY = wp.y; lookTZ = wp.z
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

        if (running) {
            val vOverC = curSpeed * 1.0295e8
            val warp = Math.pow(vOverC, 0.3)
            val atStop = now < pauseUntil && arrivalName != null

            val cal = Calendar.getInstance()
            val timeStr = "TIME %02d:%02d:%02d".format(
                cal.get(Calendar.HOUR_OF_DAY), cal.get(Calendar.MINUTE), cal.get(Calendar.SECOND)
            )
            val posStr = "POS X %+.1f Y %+.1f Z %+.1f LY".format(
                camX * 3.26156, camY * 3.26156, camZ * 3.26156
            )
            val speedStr = if (warp > 9.995) "SPEED WARP 9.99+ · %.0fc".format(vOverC)
                else "SPEED WARP ×%.1f · %.0fc".format(warp, vOverC)
            val dirStr = if (atStop && arrivalName != null) {
                val d = arrivalName!! + if (arrivalConst != null && arrivalConst != "") " · ${arrivalConst}" else ""
                "DIR → $d"
            } else {
                val dec = Math.toDegrees(kotlin.math.asin(fZ.coerceIn(-1.0, 1.0)))
                val ra = Math.toDegrees(kotlin.math.atan2(fY, fX))
                "DIR RA %.1f° DEC %+.1f°".format(ra, dec)
            }

            footerPaint.alpha = 200
            val colW = width / 4
            val fy = height - 11f * density
            canvas.drawText(timeStr, 16f * density, fy, footerPaint)
            canvas.drawText(posStr, colW.toFloat(), fy, footerPaint)
            canvas.drawText(speedStr, (colW * 2).toFloat(), fy, footerPaint)
            canvas.drawText(dirStr, (colW * 3).toFloat(), fy, footerPaint)

            drawCrosshair(canvas, cx, cy, focal)
        }

        if (running) postInvalidateDelayed(33)
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
            val sz = vx * fX + vy * fY + vz * fZ
            if (sz < 0.05) continue
            val sx = vx * rX + vy * rY + vz * rZ
            val sy = vx * uX + vy * uY + vz * uZ
            val screenX = cx + (focal * sx / sz).toFloat()
            val screenY = cy - (focal * sy / sz).toFloat()
            val rzF = sz.toFloat().coerceIn(0.12f, 6f)
            val bigCap = minOf(W, H) * (if (p.name == "Earth") 0.44f else 0.30f)
            val rPx = (p.baseR * density * 0.9f / rzF).coerceIn(5f, bigCap)
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
            r.toInt().coerceIn(0, 255),
            g.toInt().coerceIn(0, 255),
            b.toInt().coerceIn(0, 255)
        )
    }

    companion object {
        private const val MAX_DIM = 4000
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
