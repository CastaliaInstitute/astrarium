package institute.castalia.atlas.player.sky

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.view.View
import institute.castalia.atlas.player.Settings
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.min
import kotlin.math.sin

class SkyView(context: Context) : View(context) {

    private data class Star(val ra: Double, val dec: Double, val mag: Double, val bv: Double)
    private data class CountStar(val ra: Double, val dec: Double)
    private data class Seg(val ra1: Double, val dec1: Double, val ra2: Double, val dec2: Double)
    private data class Fig(val name: String, val segs: List<Seg>)
    private data class Art(val id: String, val name: String, val image: String, val w: Int, val h: Int, val pts: List<List<Double>>)

    private val stars = ArrayList<Star>()
    private val figs = ArrayList<Fig>()
    private val figByName = HashMap<String, Fig>()
    private val arts = ArrayList<Art>()
    private val artByName = HashMap<String, Art>()
    private val starByKey = HashMap<String, Star>()
    private val milkyWay = SkyMath.galacticPlane()
    private val mwClumps = ArrayList<FloatArray>()
    private val mwShaderCache = ArrayList<FloatArray>()
    private val mwShaders = ArrayList<android.graphics.RadialGradient?>()
    private val sats = Satellites()
    private var loaded = false

    @Volatile
    var tourName: String? = null
        private set

    @Volatile
    var tourExtra: String? = null
        private set

    @Volatile
    var tourStage: Int = 0
        private set

    @Volatile
    var countIndex: Int = -1
        private set

    fun countTotal(): Int = countOrder.size

    fun figStarCoords(name: String): List<Pair<Double, Double>> {
        val fig = figByName[name] ?: return emptyList()
        val out = ArrayList<Pair<Double, Double>>()
        for (s in fig.segs) {
            out.add(Pair(s.ra1, s.dec1))
            out.add(Pair(s.ra2, s.dec2))
        }
        return out
    }

    // segments as [ra1, dec1, ra2, dec2] degree quads, for figure line drawing
    fun figSegments(name: String): List<DoubleArray> {
        val fig = figByName[name] ?: return emptyList()
        return fig.segs.map { doubleArrayOf(it.ra1, it.dec1, it.ra2, it.dec2) }
    }

    private var tourStars: List<Star> = emptyList()
    private var countOrder: List<CountStar> = emptyList()

    private val density = resources.displayMetrics.density
    private val artCache = object : LinkedHashMap<String, Bitmap>(8, 1.0f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Bitmap>): Boolean {
            if (size > 8) eldest.value.recycle()
            return size > 8
        }
    }
    private val artPaint = Paint(Paint.FILTER_BITMAP_FLAG)

    private val starPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x9AF2B25C.toInt()
        strokeWidth = 1.4f * density
        strokeCap = Paint.Cap.ROUND
    }
    private val mwPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x16E8ECFF.toInt()
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xCCF2B25C.toInt()
        textSize = 15f * density
    }
    private val countPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFF2B25C.toInt()
        textSize = 13f * density
    }
    private val compassPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x80F2B25C.toInt()
        textSize = 15f * density
    }

    init {
        try {
            val raw = context.assets.open("sky/stars.json").bufferedReader().readText()
            val root = JSONObject(raw)
            val starArr = root.getJSONArray("stars")
            for (i in 0 until starArr.length()) {
                val s = starArr.getJSONArray(i)
                val st = Star(s.getDouble(0) * 15.0, s.getDouble(1), s.getDouble(2), s.optDouble(3, 0.6))
                stars.add(st)
                starByKey[key(st.ra, st.dec)] = st
            }
            val figArr = root.getJSONArray("figs")
            for (i in 0 until figArr.length()) {
                val f = figArr.getJSONObject(i)
                val segs = ArrayList<Seg>()
                val lines = f.getJSONArray("lines")
                for (j in 0 until lines.length()) {
                    val pts = lines.getJSONArray(j)
                    for (k in 0 until pts.length() - 1) {
                        val a = pts.getJSONArray(k)
                        val b = pts.getJSONArray(k + 1)
                        segs.add(Seg(a.getDouble(0), a.getDouble(1), b.getDouble(0), b.getDouble(1)))
                    }
                }
                val fig = Fig(f.getString("name"), segs)
                figs.add(fig)
                figByName[fig.name] = fig
            }
            loaded = true
        } catch (e: Exception) {
            loaded = false
        }
        val rnd = java.util.Random(42)
        for (i in milkyWay.indices step 2) {
            val l = i * 5.0
            val weight = kotlin.math.exp(-l / 130.0)
            var n = if (l < 40 || l > 320) 3 else 2
            repeat(n) {
                val ra = milkyWay[i].first + (rnd.nextDouble() - 0.5) * 8.0
                val dec = milkyWay[i].second + (rnd.nextDouble() - 0.5) * 7.0
                mwClumps.add(
                    floatArrayOf(
                        ra.toFloat(), dec.toFloat(),
                        (2.0f + rnd.nextFloat() * 3.5f),
                        ((0.05f + rnd.nextFloat() * 0.20f) * (0.35f + weight.toFloat())).coerceAtMost(0.26f)
                    )
                )
                mwShaderCache.add(floatArrayOf(-1e9f, -1e9f, -1e9f))
                mwShaders.add(null)
            }
        }
        try {
            val rawArt = context.assets.open("sky/art.json").bufferedReader().readText()
            val arr = org.json.JSONArray(rawArt)
            for (i in 0 until arr.length()) {
                val a = arr.getJSONObject(i)
                val pts = ArrayList<List<Double>>()
                val pa = a.getJSONArray("pts")
                for (j in 0 until pa.length()) {
                    val p = pa.getJSONArray(j)
                    pts.add(listOf(p.getDouble(0), p.getDouble(1), p.getDouble(2), p.getDouble(3)))
                }
                val art = Art(a.getString("id"), a.optString("name", ""), a.getString("image"), a.getInt("w"), a.getInt("h"), pts)
                arts.add(art)
                artByName[art.name] = art
            }
            sats.load(context)
        } catch (e: Exception) {
        }
    }

    fun setTour(name: String?, stage: Int, extra: String? = null) {
        if (tourName != name || stage < tourStage) {
            tourName = name
            tourStage = stage
            countIndex = -1
            rebuildTourStars()
        } else {
            tourStage = stage
        }
        tourExtra = extra
        when {
            stage == 1 && name != null -> computeTourCamera(extra)
            stage == 0 && name == null -> animateCamera(1f, 0f, 0f, 0f)
        }
        invalidate()
    }

    fun resetCamera() {
        camAnim?.cancel()
        camZoom = 1f
        camTx = 0f
        camTy = 0f
        camRoll = 0f
        invalidate()
    }

    fun debugJson(): JSONObject = JSONObject()
        .put("stars", stars.size)
        .put("figs", figs.size)
        .put("arts", arts.size)
        .put("mwClumps", mwClumps.size)
        .put("tourName", tourName ?: JSONObject.NULL)
        .put("tourStage", tourStage)
        .put("camZoom", camZoom.toDouble())
        .put("camTx", camTx.toDouble())
        .put("camTy", camTy.toDouble())
        .put("camRoll", camRoll.toDouble())
        .put("probe", probeStars())
        .put("brightSample", brightSample())

    private fun liveXY(p: FloatArray): JSONObject {
        val cx = width / 2f
        val cy = height / 2f
        val dx = camZoom * (p[0] - camTx)
        val dy = camZoom * (p[1] - camTy)
        val cr = cos(camRoll)
        val sr = sin(camRoll)
        return JSONObject()
            .put("x", (cx + cr * dx - sr * dy).toDouble())
            .put("y", (cy + sr * dx + cr * dy).toDouble())
    }

    private fun baseXY(ra: Double, dec: Double): FloatArray? {
        val lst = SkyMath.lstDeg(Calendar.getInstance(), Settings.skyLon(context).toDouble())
        val (alt, az) = SkyMath.toAltAz(ra, dec, lst, Settings.skyLat(context).toDouble())
        val phi = Math.toRadians(az - Settings.skyBottomAz(context).toDouble())
        val r = ((90.0 - alt) / 90.0).toFloat()
        if (alt < 5.0) return null
        val sx = if (Settings.skyMirror(context)) 1f else -1f
        return floatArrayOf(
            (sx * r * (width / 2f) * sin(phi)).toFloat(),
            (r * (height / 2f) * cos(phi)).toFloat()
        )
    }

    private fun probeStars(): JSONObject {
        val lst = SkyMath.lstDeg(Calendar.getInstance(), Settings.skyLon(context).toDouble())
        val lat = Settings.skyLat(context).toDouble()
        val bottomAz = Settings.skyBottomAz(context).toDouble()
        val sx = if (Settings.skyMirror(context)) 1f else -1f
        val o = JSONObject()
        val named = mapOf(
            "vega" to (279.2347 to 38.7837),
            "deneb" to (310.86 to 45.28),
            "sirius" to (101.29 to -16.72),
            "arcturus" to (213.92 to 19.18),
            "altair" to (297.7 to 8.87)
        )
        for ((name, rd) in named) {
            val (alt, az) = SkyMath.toAltAz(rd.first, rd.second, lst, lat)
            val phi = Math.toRadians(az - bottomAz)
            val r = ((90.0 - alt) / 90.0).toFloat()
            o.put(
                name, JSONObject()
                    .put("alt", alt).put("az", az)
                    .put("x", (width / 2f + sx * r * (width / 2f) * sin(phi)).toDouble())
                    .put("y", (height / 2f + r * (height / 2f) * cos(phi)).toDouble())
            )
        }
        val moon = SolarSystem.moon(Calendar.getInstance())
        val (mAlt, mAz) = SkyMath.toAltAz(moon.raDeg, moon.decDeg, lst, lat)
        o.put(
            "moon", JSONObject()
                .put("alt", mAlt).put("az", mAz)
                .put("ra", moon.raDeg).put("dec", moon.decDeg)
        )
        return o
    }

    private fun brightSample(): JSONArray {
        val arr = JSONArray()
        var n = 0
        for (s in stars) {
            if (s.mag > 0.8) continue
            val p = baseXY(s.ra, s.dec) ?: continue
            val live = liveXY(p)
            live.put("mag", s.mag).put("ra", s.ra).put("dec", s.dec)
            arr.put(live)
            if (++n >= 10) break
        }
        return arr
    }

    private var camZoom = 1f
    private var camTx = 0f
    private var camTy = 0f
    private var camRoll = 0f
    private var camAnim: android.animation.ValueAnimator? = null

    private fun animateCamera(toZoom: Float, toTx: Float, toTy: Float, toRoll: Float) {
        camAnim?.cancel()
        val fZ = camZoom
        val fX = camTx
        val fY = camTy
        val fR = camRoll
        camAnim = android.animation.ValueAnimator.ofFloat(0f, 1f).apply {
            duration = 2200
            interpolator = android.view.animation.DecelerateInterpolator()
            addUpdateListener {
                val f = it.animatedFraction
                camZoom = fZ + (toZoom - fZ) * f
                camTx = fX + (toTx - fX) * f
                camTy = fY + (toTy - fY) * f
                camRoll = fR + (toRoll - fR) * f
                invalidate()
            }
            start()
        }
    }

    private fun screenPosFor(ra: Double, dec: Double): FloatArray? {
        val lat = Settings.skyLat(context).toDouble()
        val lon = Settings.skyLon(context).toDouble()
        val bottomAz = Settings.skyBottomAz(context).toDouble()
        val mirror = Settings.skyMirror(context)
        val lst = SkyMath.lstDeg(Calendar.getInstance(), lon)
        val (alt, az) = SkyMath.toAltAz(ra, dec, lst, lat)
        if (alt < MIN_ALT) return null
        val phi = Math.toRadians(az - bottomAz)
        val r = ((90.0 - alt) / 90.0).toFloat()
        val sx = if (mirror) 1f else -1f
        return floatArrayOf(
            width / 2f + sx * r * (width / 2f) * sin(phi).toFloat(),
            height / 2f + r * (height / 2f) * cos(phi).toFloat()
        )
    }

    private fun computeTourCamera(extra: String?) {
        val pts = ArrayList<FloatArray>()
        countOrder.forEach { screenPosFor(it.ra, it.dec)?.let(pts::add) }
        val extraFig = extra?.let { figByName[it] }
        extraFig?.let { fig ->
            val seen = HashSet<String>()
            for (seg in fig.segs) {
                for (rd in listOf(seg.ra1 to seg.dec1, seg.ra2 to seg.dec2)) {
                    if (seen.add(key(rd.first, rd.second))) {
                        screenPosFor(rd.first, rd.second)?.let(pts::add)
                    }
                }
            }
        }
        if (pts.size < 2) return
        var ax = 0f
        var ay = 0f
        pts.forEach { ax += it[0]; ay += it[1] }
        ax /= pts.size
        ay /= pts.size
        var best = -1f
        var angle = 0f
        for (i in pts.indices) {
            for (j in i + 1 until pts.size) {
                val d = hypot((pts[j][0] - pts[i][0]).toDouble(), (pts[j][1] - pts[i][1]).toDouble()).toFloat()
                if (d > best) {
                    best = d
                    angle = atan2(pts[j][1] - pts[i][1], pts[j][0] - pts[i][0])
                }
            }
        }
        if (best < 10f) return
        val z = (0.62f * min(width, height) / best).coerceIn(1.5f, 4f)
        animateCamera(z, ax, ay, -angle)
    }

    fun setCountIndex(i: Int) {
        countIndex = i
        invalidate()
    }

    private fun rebuildTourStars() {
        tourStars = emptyList()
        countOrder = emptyList()
        val fig = tourName?.let { figByName[it] } ?: return
        val seen = HashSet<String>()
        val pathPts = ArrayList<Pair<Double, Double>>()
        for (seg in fig.segs) {
            for (rd in listOf(seg.ra1 to seg.dec1, seg.ra2 to seg.dec2)) {
                val k = key(rd.first, rd.second)
                if (seen.add(k)) pathPts.add(rd)
            }
        }
        tourStars = pathPts.mapNotNull { starByKey[key(it.first, it.second)] }
        val mags = pathPts.map { nearestMag(it.first, it.second) }
        val chosen = pathPts.indices
            .sortedBy { mags[it] }
            .take(5)
            .toSet()
        countOrder = pathPts.withIndex()
            .filter { it.index in chosen }
            .map { CountStar(it.value.first, it.value.second) }
    }

    private fun nearestMag(ra: Double, dec: Double): Double {
        var best = 4.5
        var bestD = 0.45
        val cosDec = cos(Math.toRadians(dec))
        for (s in stars) {
            val d = hypot((s.ra - ra) * cosDec, s.dec - dec)
            if (d < bestD) {
                bestD = d
                best = s.mag
            }
        }
        return best
    }

    public override fun onDraw(canvas: Canvas) {
        if (!loaded) return
        val lat = Settings.skyLat(context).toDouble()
        val lon = Settings.skyLon(context).toDouble()
        val bottomAz = Settings.skyBottomAz(context).toDouble()
        val mirror = Settings.skyMirror(context)
        val magLimit = Settings.skyMagLimit(context).toDouble()
        val lst = SkyMath.lstDeg(Calendar.getInstance(), lon)
        val now = System.currentTimeMillis()
        val cal = Calendar.getInstance()

        val cx = width / 2f
        val cy = height / 2f
        val rx = width / 2f
        val ry = height / 2f
        val tourArt = if (tourStage >= 2) tourName?.let { artByName[it] } else null
        val dim = tourStage >= 2

        fun projectAltAz(az: Double, alt: Double, minAlt: Double = MIN_ALT): FloatArray? {
            if (alt < minAlt) return null
            val phi = Math.toRadians(az - bottomAz)
            val r = ((90.0 - alt) / 90.0).toFloat()
            val sx = if (mirror) 1f else -1f
            return floatArrayOf(sx * r * rx * sin(phi).toFloat(), r * ry * cos(phi).toFloat())
        }

        fun project(ra: Double, dec: Double): FloatArray? {
            val (alt, az) = SkyMath.toAltAz(ra, dec, lst, lat)
            return projectAltAz(az, alt)
        }

        canvas.save()
        canvas.translate(cx, cy)
        canvas.rotate(Math.toDegrees(camRoll.toDouble()).toFloat())
        canvas.scale(camZoom, camZoom)
        canvas.translate(-camTx, -camTy)

        val mwCloudPaint = Paint(Paint.ANTI_ALIAS_FLAG)
        for ((ci, c) in mwClumps.withIndex()) {
            val p = project(c[0].toDouble(), c[1].toDouble()) ?: continue
            val r = (c[2] / 180f * min(rx, ry)) * (width / 720f).coerceIn(1f, 2.2f)
            val cached = mwShaderCache[ci]
            var sh = mwShaders[ci]
            if (sh == null || abs(p[0] - cached[0]) > 0.5f || abs(p[1] - cached[1]) > 0.5f || abs(r - cached[2]) > 0.5f) {
                sh = android.graphics.RadialGradient(
                    p[0], p[1], r,
                    intArrayOf(0x99E8ECFF.toInt(), 0x22DDE4FF.toInt(), 0x00DDE4FF),
                    floatArrayOf(0f, 0.55f, 1f),
                    android.graphics.Shader.TileMode.CLAMP
                )
                mwShaders[ci] = sh
                cached[0] = p[0]
                cached[1] = p[1]
                cached[2] = r
            }
            mwCloudPaint.shader = sh
            mwCloudPaint.alpha = (c[3] * 255).toInt()
            canvas.drawCircle(p[0], p[1], r, mwCloudPaint)
        }

        if (tourStage >= 2) {
            val art = tourName?.let { artByName[it] }
            if (art != null) drawArt(canvas, art, ::project)
            val extraArt = tourExtra?.let { artByName[it] }
            if (extraArt != null) drawArt(canvas, extraArt, ::project)
        }

        if (tourStage >= 1) {
            val names = listOfNotNull(tourName, tourExtra)
            for (figName in names) {
                figByName[figName]?.let { fig ->
                    for (seg in fig.segs) {
                        val a = project(seg.ra1, seg.dec1) ?: continue
                        val b = project(seg.ra2, seg.dec2) ?: continue
                        canvas.drawLine(a[0], a[1], b[0], b[1], linePaint)
                    }
                }
            }
        }

        val tourKeys = HashSet<String>()
        if (tourStage >= 2) tourStars.forEach { tourKeys.add(key(it.ra, it.dec)) }

        for (star in stars) {
            val fRel = Math.pow(10.0, -0.4 * (star.mag - magLimit))
            val fade = ((magLimit + 1.0 - star.mag) / 1.0).coerceIn(0.0, 1.0)
            var base = (38.0 * Math.pow(fRel, 0.4) * fade).toInt().coerceIn(0, 255)
            if (base < 4) continue
            val p = project(star.ra, star.dec) ?: continue
            val k = key(star.ra, star.dec)
            val isTour = tourStage >= 2 && tourKeys.contains(k)
            if (dim && !isTour) base = (base * 0.3f).toInt()
            val tw = 0.84 + 0.16 * sin(now * 0.0009 + star.ra * 37.7 + star.dec * 13.1)
            starPaint.color = starColor(star.bv)
            starPaint.alpha = (base * tw).toInt().coerceIn(0, 255)

            val coreR = (if (star.mag < 0.5) 2.2f else if (star.mag < 1.6) 1.8f else if (star.mag < 3.5) 1.4f else 1.1f) * density
            canvas.drawCircle(p[0], p[1], coreR, starPaint)

            if (tourStage == 3 && isTour) {
                val idx = countOrder.indexOfFirst { key(it.ra, it.dec) == k }
                if (idx in 0..countIndex && idx == countIndex) {
                    glowPaint.color = 0xFFF2B25C.toInt()
                    glowPaint.alpha = 150
                    canvas.drawCircle(p[0], p[1], 10f * density, glowPaint)
                }
            }
        }

        for (sat in sats.visible(cal, lat, lon)) {
            val p = projectAltAz(sat.azDeg, sat.altDeg) ?: continue
            starPaint.color = 0xFF7FD6FF.toInt()
            starPaint.alpha = 255
            canvas.drawCircle(p[0], p[1], 3.2f * density, starPaint)
            if (Settings.showLabels(context)) {
                canvas.drawText(sat.name.substringBefore(" (").trim(), p[0] + 10f * density, p[1] - 8f * density, countPaint)
            }
        }

        val moon = SolarSystem.moon(cal)
        val (mAltRaw, mAz) = SkyMath.toAltAz(moon.raDeg, moon.decDeg, lst, lat)
        val mAlt = mAltRaw - 0.95 * cos(Math.toRadians(mAltRaw))
        val moonP = projectAltAz(mAz, mAlt, -90.0)
        if (moonP != null && mAlt > -1.0) {
            val mr = 20f * density
            glowPaint.color = 0xFFF7EFDA.toInt()
            glowPaint.alpha = 55
            canvas.drawCircle(moonP[0], moonP[1], mr * 2.6f, glowPaint)
            starPaint.color = 0xFFF7EFDA.toInt()
            starPaint.alpha = 250
            canvas.drawCircle(moonP[0], moonP[1], mr, starPaint)
            val sunEq = SolarSystem.sunEq(cal)
            val (sAlt, sAz) = SkyMath.toAltAz(sunEq.first, sunEq.second, lst, lat)
            val sunP = projectAltAz(sAz, sAlt, -90.0)
            if (sunP != null) {
                val vx = sunP[0] - moonP[0]
                val vy = sunP[1] - moonP[1]
                val len = hypot(vx.toDouble(), vy.toDouble()).toFloat().coerceAtLeast(0.001f)
                val off = mr * (1.3f - moon.illum.toFloat()) * 1.4f
                starPaint.color = 0xFF060A1A.toInt()
                starPaint.alpha = 255
                canvas.drawCircle(moonP[0] + vx / len * off, moonP[1] + vy / len * off, mr * 1.04f, starPaint)
            }
            if (Settings.showLabels(context)) {
                labelPaint.alpha = 200
                canvas.drawText("Moon", moonP[0] + mr + 6f * density, moonP[1] + 5f * density, labelPaint)
            }
            labelPaint.alpha = 204
        }

        for (p in SolarSystem.planets(cal)) {
            val (pAlt, pAz) = SkyMath.toAltAz(p.raDeg, p.decDeg, lst, lat)
            val pp = projectAltAz(pAz, pAlt, 8.0) ?: continue
            starPaint.color = p.color
            starPaint.alpha = 255
            canvas.drawCircle(pp[0], pp[1], 3.4f * density, starPaint)
            if (Settings.showLabels(context)) {
                labelPaint.alpha = 190
                canvas.drawText(p.name, pp[0] + 10f * density, pp[1] - 8f * density, labelPaint)
                labelPaint.alpha = 204
            }
        }

        canvas.restore()

        if (tourStage == 3) {
            val cm = cameraMatrix()
            countOrder.forEachIndexed { i, cs ->
                if (i > countIndex) return@forEachIndexed
                val base = project(cs.ra, cs.dec) ?: return@forEachIndexed
                val pt = FloatArray(2)
                cm.mapPoints(pt, floatArrayOf(base[0], base[1]))
                if (i == countIndex) {
                    glowPaint.color = 0xFFF2B25C.toInt()
                    glowPaint.alpha = 150
                    canvas.drawCircle(pt[0], pt[1], 10f * density, glowPaint)
                    starPaint.color = 0xFFFFFFFF.toInt()
                    starPaint.alpha = 255
                    canvas.drawCircle(pt[0], pt[1], 2.6f * density, starPaint)
                }
                canvas.drawText((i + 1).toString(), pt[0] + 7f * density, pt[1] - 7f * density, countPaint)
            }
        }

        if (tourStage >= 2) {
            val title = listOfNotNull(tourName, tourExtra).joinToString(" & ")
            if (title.isNotEmpty()) {
                val tw2 = labelPaint.measureText(title)
                canvas.drawText(title, cx - tw2 / 2f, 60f * density, labelPaint)
            }
        }

        val names = listOf("N", "E", "S", "W")
        val b = ((Settings.skyBottomAz(context) / 90f).toInt() + 4) % 4
        val left = (b + if (mirror) 3 else 1) % 4
        val right = (b + if (mirror) 1 else 3) % 4
        canvas.drawText(names[b], cx - compassPaint.measureText(names[b]) / 2f, height - 16f, compassPaint)
        canvas.drawText(names[(b + 2) % 4], cx - compassPaint.measureText(names[(b + 2) % 4]) / 2f, 30f, compassPaint)
        canvas.drawText(names[left], 18f, cy + compassPaint.textSize / 3f, compassPaint)
        canvas.drawText(names[right], width - 18f - compassPaint.measureText(names[right]), cy + compassPaint.textSize / 3f, compassPaint)
    }

    private fun drawArt(canvas: Canvas, art: Art, project: (Double, Double) -> FloatArray?) {
        if (art.pts.size < 2) return
        val srcAll = ArrayList<FloatArray>()
        val dstAll = ArrayList<FloatArray>()
        for (p in art.pts) {
            val d = project(p[0], p[1]) ?: continue
            srcAll.add(floatArrayOf(p[2].toFloat(), p[3].toFloat()))
            dstAll.add(d)
        }
        if (srcAll.size < 2) return
        val mirror = Settings.skyMirror(context)
        val counts = intArrayOf(min(srcAll.size, 4), min(srcAll.size, 3), 2)
        for (n in counts) {
            val src = FloatArray(n * 2)
            val dst = FloatArray(n * 2)
            for (i in 0 until n) {
                val sx = if (n == 2 && mirror) art.w - srcAll[i][0] else srcAll[i][0]
                src[i * 2] = sx
                src[i * 2 + 1] = srcAll[i][1]
                dst[i * 2] = dstAll[i][0]
                dst[i * 2 + 1] = dstAll[i][1]
            }
            val m = Matrix()
            val ok = try {
                m.setPolyToPoly(src, 0, dst, 0, n)
            } catch (e: Exception) {
                false
            }
            if (ok) {
                artPaint.alpha = 225
                canvas.drawBitmap(artBitmap(art.image) ?: return, m, artPaint)
                return
            }
        }
    }

    private fun artBitmap(image: String): Bitmap? {
        artCache[image]?.let { return it }
        return try {
            val opts = BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.RGB_565 }
            context.assets.open("sky/art/$image").use { BitmapFactory.decodeStream(it, null, opts) }
                ?.let { bmp ->
                    artCache[image] = bmp
                    bmp
                }
        } catch (e: Exception) {
            null
        }
    }

    private fun cameraMatrix(): Matrix = Matrix().apply {
        postTranslate(width / 2f, height / 2f)
        postRotate(Math.toDegrees(camRoll.toDouble()).toFloat())
        postScale(camZoom, camZoom)
        postTranslate(-camTx, -camTy)
    }

    private fun starColor(bv: Double): Int {
        val t = ((bv + 0.2) / 2.6).coerceIn(0.0, 1.0).toFloat()
        val r = 0.60f + 0.40f * t
        val g = 0.72f + 0.24f * t
        val b = 1.00f - 0.60f * t
        return Color.rgb((r * 255).toInt(), (g * 255).toInt(), (b * 255).toInt())
    }

    private fun key(ra: Double, dec: Double): String = "${Math.round(ra * 10)}:${Math.round(dec * 10)}"

    companion object {
        private const val MIN_ALT = 5.0
    }
}
