package institute.castalia.atlas.player.sky

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import institute.castalia.atlas.player.Settings
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan
import kotlin.concurrent.thread

class SkyView(context: Context) : View(context) {
    private val verticalFovDegrees = 60.0
    @Volatile private var windowedMode = Settings.skyWindowed(context)
    @Volatile private var projectorSensors: ProjectorSensors? = null
    private var smoothedProjectorAltitude: Double? = null
    private var cameraAzOffsetDegrees = 0f
    private var cameraPitchOffsetDegrees = 0f
    private val heldPanKeys = HashSet<Int>()
    @Volatile private var joystickYaw = 0f
    @Volatile private var joystickPitch = 0f
    private var panVelocityAz = 0f
    private var panVelocityAlt = 0f
    private var panFrameTime = 0L
    private var hoverX = Float.NaN
    private var hoverY = Float.NaN
    private var hoverLabel: String? = null
    private data class HoverTarget(val x: Float, val y: Float, val name: String, val radius: Float)
    private val hoverPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val cameraPanFrame = object : Runnable {
        override fun run() {
            val now = System.nanoTime()
            val dt = if (panFrameTime == 0L) 0.016f else ((now - panFrameTime) / 1e9).toFloat().coerceIn(0f, 0.05f)
            panFrameTime = now
            val keyYaw = (if (KeyEvent.KEYCODE_DPAD_RIGHT in heldPanKeys) 1f else 0f) -
                (if (KeyEvent.KEYCODE_DPAD_LEFT in heldPanKeys) 1f else 0f)
            val keyPitch = (if (KeyEvent.KEYCODE_DPAD_UP in heldPanKeys) 1f else 0f) -
                (if (KeyEvent.KEYCODE_DPAD_DOWN in heldPanKeys) 1f else 0f)
            val targetAz = if (joystickYaw != 0f) joystickYaw * PAN_SPEED_AZ else keyYaw * PAN_SPEED_AZ
            val targetAlt = if (joystickPitch != 0f) joystickPitch * PAN_SPEED_ALT else keyPitch * PAN_SPEED_ALT
            val blend = (dt * 9f).coerceAtMost(1f)
            panVelocityAz += (targetAz - panVelocityAz) * blend
            panVelocityAlt += (targetAlt - panVelocityAlt) * blend
            cameraAzOffsetDegrees = (cameraAzOffsetDegrees + panVelocityAz * dt) % 360f
            cameraPitchOffsetDegrees = (cameraPitchOffsetDegrees + panVelocityAlt * dt).coerceIn(-90f, 90f)
            invalidate()
            if (heldPanKeys.isNotEmpty() || joystickYaw != 0f || joystickPitch != 0f || abs(panVelocityAz) > 0.05f || abs(panVelocityAlt) > 0.05f) {
                postOnAnimation(this)
            } else {
                panFrameTime = 0L
            }
        }
    }

    private data class Star(
        val ra: Double, val dec: Double, val mag: Double, val bv: Double,
        val pmRaMasYr: Double = 0.0, val pmDecMasYr: Double = 0.0, val distancePc: Double = 0.0,
        val radialVelocityKmS: Double = Double.NaN,
        val referenceEpoch: Double = 2000.0,
        var cachedYear: Double = Double.NaN, var cachedRa: Double = ra, var cachedDec: Double = dec
    )

    private data class NaturalMoonPoint(val name: String, val parent: String, val raDeg: Double, val decDeg: Double, val label: Boolean)
    private data class CountStar(val ra: Double, val dec: Double)
    private data class NamedStarPosition(val name: String, val ra: Double, val dec: Double, val motion: Star?)
    private data class Seg(
        val ra1: Double, val dec1: Double, val ra2: Double, val dec2: Double,
        val pmRa1: Double = 0.0, val pmDec1: Double = 0.0,
        val epoch1: Double = 2000.0,
        val pmRa2: Double = 0.0, val pmDec2: Double = 0.0, val epoch2: Double = 2000.0,
        val distance1Pc: Double = 0.0, val radialVelocity1KmS: Double = Double.NaN,
        val distance2Pc: Double = 0.0, val radialVelocity2KmS: Double = Double.NaN
    )
    private data class Fig(val name: String, val segs: List<Seg>)
    private data class Art(val id: String, val name: String, val image: String, val w: Int, val h: Int, val pts: List<List<Double>>)

    private val stars = ArrayList<Star>()
    private val figs = ArrayList<Fig>()
    private val figByName = HashMap<String, Fig>()
    private val arts = ArrayList<Art>()
    private val artByName = HashMap<String, Art>()
    private val starByKey = HashMap<String, Star>()
    private val namedStars = ArrayList<NamedStarPosition>()
    private val milkyWay = SkyMath.galacticPlane()
    private val mwClumps = ArrayList<FloatArray>()
    private val mwShaderCache = ArrayList<FloatArray>()
    private val mwShaders = ArrayList<android.graphics.RadialGradient?>()
    private val sats = Satellites.shared()
    private val ufoSightings = UfoSightings()
    @Volatile private var loaded = false
    private val stellarEpochYear: Double
        get() = SkyTime.decimalYear()

    fun setStellarEpochYear(year: Double) {
        if (!year.isFinite()) return
        SkyTime.setYear(year.toInt().coerceIn(SkyTime.MIN_YEAR, SkyTime.MAX_YEAR))
        postInvalidateOnAnimation()
    }

    fun setSkyTimeMillis(timestampMs: Long) {
        SkyTime.setInstant(timestampMs)
        postInvalidateOnAnimation()
    }

    fun skyTimeMillis(): Long = SkyTime.nowMillis()

    fun stellarEpochYear(): Double = SkyTime.calendarYear().toDouble()

    private fun skyCalendar(): Calendar = SkyTime.calendar()

    private fun naturalMoonDirections(cal: Calendar): List<NaturalMoonPoint> {
        val earth = SolarSystem.heliocentricPositionAu("Earth", cal, requestLunarData = false, useCachedLunarData = false)
            ?: return emptyList()
        return NaturalSatelliteEphemeris.skyStatesAt(cal).mapNotNull { moon ->
            val x = moon.state.xKm / 149_597_870.7 - earth.first
            val y = moon.state.yKm / 149_597_870.7 - earth.second
            val z = moon.state.zKm / 149_597_870.7 - earth.third
            val equatorial = SolarSystem.geocentricEclipticJ2000ToEquatorial(x, y, z, cal)
            NaturalMoonPoint(moon.target.name, moon.system.parent, equatorial.first, equatorial.second, moon.labelInSky)
        }
    }

    private fun positionAt(raDeg: Double, decDeg: Double, pmRaMasYr: Double, pmDecMasYr: Double, fromYear: Double, year: Double,
                           distancePc: Double = 0.0, radialVelocityKmS: Double = Double.NaN): Pair<Double, Double> {
        if (pmRaMasYr == 0.0 && pmDecMasYr == 0.0 &&
            (distancePc <= 0.0 || !radialVelocityKmS.isFinite())) {
            return SkyMath.precessEquatorial(raDeg, decDeg, fromYear, year)
        }
        val a = Math.toRadians(raDeg)
        val d = Math.toRadians(decDeg)
        // Catalog positions are apparent directions observed at their reference epoch.
        // Advance from that observation epoch to the selected observation epoch; do not
        // subtract stellar light time a second time.
        val years = year - fromYear
        val ma = pmRaMasYr * Math.PI / (180.0 * 3600.0 * 1000.0)
        val md = pmDecMasYr * Math.PI / (180.0 * 3600.0 * 1000.0)
        val x0 = cos(d) * cos(a)
        val y0 = cos(d) * sin(a)
        val z0 = sin(d)
        // Gaia pmRA is mu_alpha*cos(dec), so these are local east/north tangent components.
        val eastX = -sin(a)
        val eastY = cos(a)
        val northX = -sin(d) * cos(a)
        val northY = -sin(d) * sin(a)
        val northZ = cos(d)
        if (distancePc > 0.0 && radialVelocityKmS.isFinite()) {
            val masToRad = Math.PI / (180.0 * 3600.0 * 1000.0)
            val radialPcPerYear = radialVelocityKmS * 1.022712165e-6
            val vx = radialPcPerYear * x0 + distancePc * masToRad * (pmRaMasYr * eastX + pmDecMasYr * northX)
            val vy = radialPcPerYear * y0 + distancePc * masToRad * (pmRaMasYr * eastY + pmDecMasYr * northY)
            val vz = radialPcPerYear * z0 + distancePc * masToRad * pmDecMasYr * northZ
            val x = distancePc * x0 + years * vx
            val y = distancePc * y0 + years * vy
            val z = distancePc * z0 + years * vz
            val movedRa = SkyMath.norm(Math.toDegrees(atan2(y, x)))
            val movedDec = Math.toDegrees(kotlin.math.asin((z / sqrt(x * x + y * y + z * z).coerceAtLeast(1e-30)).coerceIn(-1.0, 1.0)))
            return SkyMath.precessEquatorial(movedRa, movedDec, fromYear, year)
        }
        val speed = hypot(ma, md)
        val angle = speed * years
        val (x, y, z) = if (speed <= 1e-30) Triple(x0, y0, z0) else {
            val tx = (ma * eastX + md * northX) / speed
            val ty = (ma * eastY + md * northY) / speed
            val tz = md * northZ / speed
            val c = cos(angle)
            val s = sin(angle)
            Triple(x0 * c + tx * s, y0 * c + ty * s, z0 * c + tz * s)
        }
        val norm = sqrt(x * x + y * y + z * z).coerceAtLeast(1e-15)
        val movedRa = SkyMath.norm(Math.toDegrees(atan2(y, x)))
        val movedDec = Math.toDegrees(kotlin.math.asin((z / norm).coerceIn(-1.0, 1.0)))
        return SkyMath.precessEquatorial(movedRa, movedDec, fromYear, year)
    }

    private fun positionAt(star: Star, year: Double): Pair<Double, Double> {
        if (star.cachedYear != year) {
            val p = positionAt(star.ra, star.dec, star.pmRaMasYr, star.pmDecMasYr, star.referenceEpoch, year,
                star.distancePc, star.radialVelocityKmS)
            star.cachedRa = p.first
            star.cachedDec = p.second
            star.cachedYear = year
        }
        return star.cachedRa to star.cachedDec
    }

    private fun segmentPoint(ra: Double, dec: Double, pmRa: Double, pmDec: Double, referenceEpoch: Double, year: Double,
                             distancePc: Double = 0.0, radialVelocityKmS: Double = Double.NaN): Pair<Double, Double> =
        positionAt(ra, dec, pmRa, pmDec, referenceEpoch, year, distancePc, radialVelocityKmS)

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
        if (!loaded) return emptyList()
        val fig = figByName[name] ?: return emptyList()
        val out = ArrayList<Pair<Double, Double>>()
        for (s in fig.segs) {
            out.add(segmentPoint(s.ra1, s.dec1, s.pmRa1, s.pmDec1, s.epoch1, stellarEpochYear, s.distance1Pc, s.radialVelocity1KmS))
            out.add(segmentPoint(s.ra2, s.dec2, s.pmRa2, s.pmDec2, s.epoch2, stellarEpochYear, s.distance2Pc, s.radialVelocity2KmS))
        }
        return out
    }

    // segments as [ra1, dec1, ra2, dec2] degree quads, for figure line drawing
    fun figSegments(name: String): List<DoubleArray> {
        if (!loaded) return emptyList()
        val fig = figByName[name] ?: return emptyList()
        return fig.segs.map {
            val a = segmentPoint(it.ra1, it.dec1, it.pmRa1, it.pmDec1, it.epoch1, stellarEpochYear, it.distance1Pc, it.radialVelocity1KmS)
            val b = segmentPoint(it.ra2, it.dec2, it.pmRa2, it.pmDec2, it.epoch2, stellarEpochYear, it.distance2Pc, it.radialVelocity2KmS)
            doubleArrayOf(a.first, a.second, b.first, b.second)
        }
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
    private val satelliteTrackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x667FD6FF
        style = Paint.Style.STROKE
        strokeWidth = 1.1f * density
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
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
        val appContext = context.applicationContext
        sats.onDataChanged = { postInvalidateOnAnimation() }
        JplLunarEphemeris.onDataChanged = { postInvalidateOnAnimation() }
        JplPlanetEphemeris.initialize(appContext.cacheDir)
        JplSmallBodyEphemeris.initialize(appContext.cacheDir)
        JplPlanetEphemeris.onDataChanged = { postInvalidateOnAnimation() }
        NaturalSatelliteEphemeris.initialize(appContext.cacheDir)
        NaturalSatelliteEphemeris.onDataChanged = { postInvalidateOnAnimation() }
        thread(name = "sky-assets") {
            loadSkyAssets(appContext)
            post {
                loaded = stars.isNotEmpty()
                rebuildTourStars()
                if (loaded && tourStage == 1 && tourName != null) computeTourCamera(tourExtra)
                invalidate()
            }
        }
        val rnd = java.util.Random(42)
        for (i in milkyWay.indices step 2) {
            val l = i * 5.0
            val weight = kotlin.math.exp(-l / 130.0)
            val n = if (l < 40 || l > 320) 3 else 2
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
    }

    private fun loadSkyAssets(context: Context) {
        try {
            val raw = context.assets.open("sky/stars.json").bufferedReader().readText()
            val root = JSONObject(raw)
            val starArr = root.getJSONArray("stars")
            for (i in 0 until starArr.length()) {
                val s = starArr.getJSONArray(i)
                val st = Star(s.getDouble(0) * 15.0, s.getDouble(1), s.getDouble(2), s.optDouble(3, 0.6),
                    s.optDouble(4, 0.0), s.optDouble(5, 0.0), s.optDouble(6, 0.0), s.optDouble(8, Double.NaN), s.optDouble(7, 2000.0))
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
                        segs.add(Seg(a.getDouble(0), a.getDouble(1), b.getDouble(0), b.getDouble(1),
                            a.optDouble(2, 0.0), a.optDouble(3, 0.0), a.optDouble(5, 2000.0),
                            b.optDouble(2, 0.0), b.optDouble(3, 0.0), b.optDouble(5, 2000.0),
                            a.optDouble(4, 0.0), a.optDouble(6, Double.NaN), b.optDouble(4, 0.0), b.optDouble(6, Double.NaN)))
                    }
                }
                val fig = Fig(f.getString("name"), segs)
                figs.add(fig)
                figByName[fig.name] = fig
            }
        } catch (e: Exception) {
            android.util.Log.e("SkyView", "Could not load star catalog", e)
        }
        try {
            val labels = JSONArray(context.assets.open("sky/star-names.json").bufferedReader().use { it.readText() })
            for (i in 0 until labels.length()) {
                val item = labels.getJSONObject(i)
                val x = item.getDouble("x")
                val y = item.getDouble("y")
                val z = item.getDouble("z")
                if (hypot(x, y) < 1e-9) continue
                val ra = ((Math.toDegrees(atan2(y, x)) % 360.0) + 360.0) % 360.0
                val dec = Math.toDegrees(atan2(z, hypot(x, y)))
                namedStars.add(NamedStarPosition(item.getString("n"), ra, dec, nearestCatalogStar(ra, dec, 0.5)))
            }
        } catch (_: Exception) { }
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
            ufoSightings.load(context)
        } catch (e: Exception) {
            android.util.Log.e("SkyView", "Could not load constellation art", e)
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
        stopCameraPan()
        camAnim?.cancel()
        camZoom = 1f
        camTx = 0f
        camTy = 0f
        camRoll = 0f
        cameraAzOffsetDegrees = 0f
        cameraPitchOffsetDegrees = 0f
        invalidate()
    }

    fun rotateCameraBy(azimuthDegrees: Float, altitudeDegrees: Float) {
        camAnim?.cancel()
        cameraAzOffsetDegrees = (cameraAzOffsetDegrees + azimuthDegrees) % 360f
        cameraPitchOffsetDegrees = (cameraPitchOffsetDegrees + altitudeDegrees).coerceIn(-90f, 90f)
        invalidate()
    }

    fun setCameraPanKey(keyCode: Int, pressed: Boolean) {
        if (pressed) {
            if (!windowedMode) {
                // At zenith, horizontal rotation is only a roll around the center. Switch
                // to the projector-aimed field so horizontal input pans across the sky.
                // Keep this interaction-only so full-sky remains the saved boot mode.
                windowedMode = true
            }
            heldPanKeys.add(keyCode)
        } else heldPanKeys.remove(keyCode)
        if (heldPanKeys.isNotEmpty() || abs(panVelocityAz) > 0.05f || abs(panVelocityAlt) > 0.05f) {
            if (panFrameTime == 0L) postOnAnimation(cameraPanFrame)
        }
    }

    fun setJoystickAxes(yaw: Float, pitch: Float) {
        joystickYaw = deadzone(yaw)
        joystickPitch = deadzone(pitch)
        if (abs(joystickYaw) > JOYSTICK_DEADZONE || abs(joystickPitch) > JOYSTICK_DEADZONE) {
            if (!windowedMode) {
                // Joystick steering should use the same projector-aimed, level horizon as the D-pad.
                windowedMode = true
            }
            if (panFrameTime == 0L) postOnAnimation(cameraPanFrame)
        }
    }

    private fun deadzone(value: Float): Float {
        val v = value.coerceIn(-1f, 1f)
        val a = abs(v)
        return if (a <= JOYSTICK_DEADZONE) 0f else (if (v < 0f) -1f else 1f) * ((a - JOYSTICK_DEADZONE) / (1f - JOYSTICK_DEADZONE))
    }

    fun stopCameraPan() {
        heldPanKeys.clear()
        panVelocityAz = 0f
        panVelocityAlt = 0f
        panFrameTime = 0L
        removeCallbacks(cameraPanFrame)
    }

    override fun onHoverEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_HOVER_MOVE, MotionEvent.ACTION_HOVER_ENTER -> {
                hoverX = event.x
                hoverY = event.y
                hoverLabel = identifyAt(event.x, event.y)
                invalidate()
                return true
            }
            MotionEvent.ACTION_HOVER_EXIT -> {
                hoverX = Float.NaN
                hoverY = Float.NaN
                hoverLabel = null
                invalidate()
                return true
            }
        }
        return super.onHoverEvent(event)
    }

    private fun identifyAt(x: Float, y: Float): String? {
        if (!loaded || width <= 0 || height <= 0) return null
        val cal = skyCalendar()
        val lat = Settings.skyLat(context).toDouble()
        val lon = Settings.skyLon(context).toDouble()
        val lst = SkyMath.lstDeg(cal, lon)
        val matrix = cameraMatrix()
        val targets = ArrayList<HoverTarget>()
        fun add(az: Double, alt: Double, name: String, radius: Float = 16f * density) {
            val base = projectAltAz(az, alt, -90.0) ?: return
            val point = floatArrayOf(width / 2f + base[0], height / 2f + base[1])
            matrix.mapPoints(point)
            targets.add(HoverTarget(point[0], point[1], name, radius))
        }
        for (star in stars) {
            if (star.mag > 3.5) continue
            val (ra, dec) = positionAt(star, stellarEpochYear)
            val (alt, az) = SkyMath.toAltAz(ra, dec, lst, lat)
            val name = namedStar(star) ?: "Star · RA ${"%.1f".format(ra)}° Dec ${"%.1f".format(dec)}°"
            add(az, alt, name, 14f * density)
        }
        val moon = SolarSystem.moon(cal)
        val (moonAlt, moonAz) = SkyMath.toAltAz(moon.raDeg, moon.decDeg, lst, lat)
        add(moonAz, moonAlt, "Moon", 24f * density)
        for (naturalMoon in naturalMoonDirections(cal)) {
            val (alt, az) = SkyMath.toAltAz(naturalMoon.raDeg, naturalMoon.decDeg, lst, lat)
            add(az, alt, "${naturalMoon.name} · ${naturalMoon.parent}", 12f * density)
        }
        val sun = SolarSystem.sunEq(cal)
        val (sunAlt, sunAz) = SkyMath.toAltAz(sun.first, sun.second, lst, lat)
        add(sunAz, sunAlt, "Sun", 18f * density)
        for (planet in SolarSystem.planets(cal)) {
            val (alt, az) = SkyMath.toAltAz(planet.raDeg, planet.decDeg, lst, lat)
            add(az, alt, planet.name, 18f * density)
        }
        for (sat in sats.visible(cal, lat, lon)) add(sat.azDeg, sat.altDeg, sat.name.substringBefore(" (").trim(), 17f * density)
        for (marker in ufoSightings.visible(cal, lat, lon, Settings.skyAltitudeKm(context).toDouble())) {
            add(marker.azimuthDeg, marker.elevationDeg, "Reported UAP · ${marker.sighting.source}", 24f * density)
        }
        val nearest = targets.asSequence()
            .map { it to hypot((it.x - x).toDouble(), (it.y - y).toDouble()).toFloat() }
            .filter { (target, dist) -> dist <= target.radius }
            .minByOrNull { it.second }
        return nearest?.first?.name
    }

    private fun nearestCatalogStar(ra: Double, dec: Double, limit: Double): Star? = stars.asSequence()
        .map { it to hypot((it.ra - ra) * cos(Math.toRadians(dec)), it.dec - dec) }
        .filter { it.second < limit }
        .minByOrNull { it.second }?.first

    private fun namedStar(star: Star): String? = when {
        else -> namedStars.asSequence()
            .map {
                val p = it.motion?.let { moving -> positionAt(moving, stellarEpochYear) } ?: (it.ra to it.dec)
                it to hypot((p.first - positionAt(star, stellarEpochYear).first) * cos(Math.toRadians(positionAt(star, stellarEpochYear).second)), p.second - positionAt(star, stellarEpochYear).second)
            }
            .filter { it.second < 0.25 }
            .minByOrNull { it.second }?.first?.name
    }

    fun toggleWindowedMode(): Boolean {
        windowedMode = !windowedMode
        Settings.setSkyWindowed(context, windowedMode)
        invalidate()
        return windowedMode
    }

    fun updateProjectorSensors(snapshot: ProjectorSensors?) {
        projectorSensors = snapshot
        val target = snapshot?.pointingAltitudeDegrees
        if (target != null) {
            val old = smoothedProjectorAltitude
            smoothedProjectorAltitude = if (old == null) target else old + (target - old) * 0.25
        }
        invalidate()
    }

    fun debugJson(): JSONObject = JSONObject()
        .put("loaded", loaded)
        .put("stars", if (loaded) stars.size else 0)
        .put("figs", if (loaded) figs.size else 0)
        .put("arts", if (loaded) arts.size else 0)
        .put("mwClumps", mwClumps.size)
        .put("tourName", tourName ?: JSONObject.NULL)
        .put("tourStage", tourStage)
        .put("camZoom", camZoom.toDouble())
        .put("camTx", camTx.toDouble())
        .put("camTy", camTy.toDouble())
        .put("camRoll", camRoll.toDouble())
        .put("viewMode", if (windowedMode) "windowed" else "dome")
        .put("verticalFovDegrees", if (windowedMode) verticalFovDegrees else JSONObject.NULL)
        .put("stellarEpochYear", stellarEpochYear)
        .put("satelliteArchive", sats.archiveStatus(skyCalendar()))
        .put("lunarEphemeris", JSONObject().apply {
            val coverage = JplLunarEphemeris.coverage(skyCalendar())
            put("state", coverage.state)
            put("source", coverage.source)
            put("sampleCount", coverage.sampleCount)
        })
        .put("naturalSatelliteEphemeris", NaturalSatelliteEphemeris.skyCoverage(skyCalendar()))
        .put("cockpitOverlay", Settings.cockpitOverlay(context))
        .put("cameraAzimuthDegrees", cameraAzimuthDegrees())
        .put("cameraAltitudeDegrees", cameraAltitudeDegrees())
        .put("projectorSensors", projectorSensors?.toJson() ?: ProjectorSensors.unavailableJson())
        .put("probe", probeStars())
        .put("brightSample", brightSample())

    fun cameraStateJson(): JSONObject = JSONObject()
        .put("viewMode", if (windowedMode) "windowed" else "dome")
        .put("cameraAzimuthDegrees", cameraAzimuthDegrees())
        .put("cameraAltitudeDegrees", cameraAltitudeDegrees())

    private fun cameraAzimuthDegrees(): Double =
        (((Settings.skyBottomAz(context) + cameraAzOffsetDegrees) % 360f + 360f) % 360f).toDouble()

    private fun cameraAltitudeDegrees(): Double {
        val base = when {
            windowedMode -> smoothedProjectorAltitude ?: 90.0
            else -> 90.0
        }
        return (base + cameraPitchOffsetDegrees.toDouble()).coerceIn(0.0, 90.0)
    }

    /** Returns coordinates relative to the view center after applying the projector camera pose. */
    private fun projectAltAz(azimuth: Double, altitude: Double, minAltitude: Double = MIN_ALT): FloatArray? {
        if (altitude < minAltitude || width <= 0 || height <= 0) return null

        val az = Math.toRadians(azimuth)
        val alt = Math.toRadians(altitude)
        val heading = Math.toRadians(cameraAzimuthDegrees())
        val cameraAlt = Math.toRadians(cameraAltitudeDegrees())

        val east = cos(alt) * sin(az)
        val north = cos(alt) * cos(az)
        val up = sin(alt)

        val forwardEast = cos(cameraAlt) * sin(heading)
        val forwardNorth = cos(cameraAlt) * cos(heading)
        val forwardUp = sin(cameraAlt)
        val rightEast = -cos(heading)
        val rightNorth = sin(heading)
        val downEast = sin(cameraAlt) * sin(heading)
        val downNorth = sin(cameraAlt) * cos(heading)
        val downUp = -cos(cameraAlt)

        val forward = east * forwardEast + north * forwardNorth + up * forwardUp
        val right = east * rightEast + north * rightNorth
        val down = east * downEast + north * downNorth + up * downUp
        val xSign = if (Settings.skyMirror(context)) -1.0 else 1.0

        if (windowedMode) {
            if (forward <= 0.0) return null
            val tanHalfVertical = tan(Math.toRadians(verticalFovDegrees / 2.0))
            val tanHalfHorizontal = tanHalfVertical * width.toDouble() / height.toDouble()
            val x = xSign * right / (forward * tanHalfHorizontal)
            val y = down / (forward * tanHalfVertical)
            if (abs(x) > 2.5 || abs(y) > 2.5) return null
            return floatArrayOf((x * width / 2.0).toFloat(), (y * height / 2.0).toFloat())
        }

        if (forward < 0.0) return null
        val theta = acos(forward.coerceIn(-1.0, 1.0))
        val sinTheta = sqrt((1.0 - forward * forward).coerceAtLeast(0.0))
        if (sinTheta < 1e-6) return floatArrayOf(0f, 0f)
        val radius = theta / (Math.PI / 2.0)
        val x = xSign * right / sinTheta * radius * width / 2.0
        val y = down / sinTheta * radius * height / 2.0
        return floatArrayOf(x.toFloat(), y.toFloat())
    }

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
        val lst = SkyMath.lstDeg(skyCalendar(), Settings.skyLon(context).toDouble())
        val (alt, az) = SkyMath.toAltAz(ra, dec, lst, Settings.skyLat(context).toDouble())
        return projectAltAz(az, alt)
    }

    private fun probeStars(): JSONObject {
        val lst = SkyMath.lstDeg(skyCalendar(), Settings.skyLon(context).toDouble())
        val lat = Settings.skyLat(context).toDouble()
        val o = JSONObject()
        val named = mapOf(
            "vega" to (279.2347 to 38.7837),
            "deneb" to (310.86 to 45.28),
            "sirius" to (101.29 to -16.72),
            "arcturus" to (213.92 to 19.18),
            "altair" to (297.7 to 8.87)
        )
        for ((name, rd) in named) {
            val namedMotion = namedStars.firstOrNull { it.name.equals(name, ignoreCase = true) }?.motion
            val coords = namedMotion?.let { positionAt(it, stellarEpochYear) }
                ?: SkyMath.precessEquatorial(rd.first, rd.second, 2000.0, stellarEpochYear)
            val (alt, az) = SkyMath.toAltAz(coords.first, coords.second, lst, lat)
            val p = projectAltAz(az, alt)
            o.put(
                name, JSONObject()
                    .put("alt", alt).put("az", az)
                    .put("x", p?.let { (width / 2f + it[0]).toDouble() } ?: JSONObject.NULL)
                    .put("y", p?.let { (height / 2f + it[1]).toDouble() } ?: JSONObject.NULL)
            )
        }
        val moon = SolarSystem.moon(skyCalendar())
        val (mAlt, mAz) = SkyMath.toAltAz(moon.raDeg, moon.decDeg, lst, lat)
        o.put(
            "moon", JSONObject()
                .put("alt", mAlt).put("az", mAz)
                .put("ra", moon.raDeg).put("dec", moon.decDeg)
                .put("source", moon.source)
        )
        return o
    }

    private fun brightSample(): JSONArray {
        val arr = JSONArray()
        if (!loaded) return arr
        var n = 0
        for (s in stars) {
            if (s.mag > 0.8) continue
            val apparent = positionAt(s, stellarEpochYear)
            val p = baseXY(apparent.first, apparent.second) ?: continue
            val live = liveXY(p)
            live.put("mag", s.mag).put("ra", apparent.first).put("dec", apparent.second)
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
        val lst = SkyMath.lstDeg(skyCalendar(), lon)
        val (dateRa, dateDec) = SkyMath.precessJ2016(ra, dec, stellarEpochYear)
        val (alt, az) = SkyMath.toAltAz(dateRa, dateDec, lst, lat)
        val p = projectAltAz(az, alt) ?: return null
        return floatArrayOf(width / 2f + p[0], height / 2f + p[1])
    }

    private fun computeTourCamera(extra: String?) {
        if (!loaded) return
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
        if (!loaded) return
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
        val magLimit = Settings.skyMagLimit(context).toDouble()
        val lst = SkyMath.lstDeg(skyCalendar(), lon)
        val now = System.currentTimeMillis()
        val cal = skyCalendar()

        val cx = width / 2f
        val cy = height / 2f
        val rx = width / 2f
        val ry = height / 2f
        val tourArt = if (tourStage >= 2) tourName?.let { artByName[it] } else null
        val dim = tourStage >= 2

        fun project(ra: Double, dec: Double): FloatArray? {
            val (alt, az) = SkyMath.toAltAz(ra, dec, lst, lat)
            return projectAltAz(az, alt)
        }

        fun projectMotion(ra: Double, dec: Double, pmRa: Double, pmDec: Double, referenceEpoch: Double,
                          distancePc: Double = 0.0, radialVelocityKmS: Double = Double.NaN): FloatArray? {
            val apparent = segmentPoint(ra, dec, pmRa, pmDec, referenceEpoch, stellarEpochYear, distancePc, radialVelocityKmS)
            return project(apparent.first, apparent.second)
        }

        fun projectJ2000(ra: Double, dec: Double): FloatArray? {
            val dateCoords = SkyMath.precessEquatorial(ra, dec, 2000.0, stellarEpochYear)
            return project(dateCoords.first, dateCoords.second)
        }

        fun projectArtAnchor(ra: Double, dec: Double): FloatArray? {
            val star = nearestCatalogStar(ra, dec, 0.5)
            if (star != null) {
                val moved = positionAt(star, stellarEpochYear)
                return project(moved.first, moved.second)
            }
            return projectJ2000(ra, dec)
        }

        canvas.save()
        canvas.translate(cx, cy)
        canvas.rotate(Math.toDegrees(camRoll.toDouble()).toFloat())
        canvas.scale(camZoom, camZoom)
        canvas.translate(-camTx, -camTy)

        val mwCloudPaint = Paint(Paint.ANTI_ALIAS_FLAG)
        for ((ci, c) in mwClumps.withIndex()) {
            val p = projectJ2000(c[0].toDouble(), c[1].toDouble()) ?: continue
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

        if (tourStage >= 2 && Settings.constellationArt(context)) {
            val art = tourName?.let { artByName[it] }
            if (art != null) drawArt(canvas, art, ::projectArtAnchor)
            val extraArt = tourExtra?.let { artByName[it] }
            if (extraArt != null) drawArt(canvas, extraArt, ::projectArtAnchor)
        }

        if (tourStage >= 1 && Settings.constellationLines(context)) {
            val names = listOfNotNull(tourName, tourExtra)
            for (figName in names) {
                figByName[figName]?.let { fig ->
                    for (seg in fig.segs) {
                        val a = projectMotion(seg.ra1, seg.dec1, seg.pmRa1, seg.pmDec1, seg.epoch1, seg.distance1Pc, seg.radialVelocity1KmS) ?: continue
                        val b = projectMotion(seg.ra2, seg.dec2, seg.pmRa2, seg.pmDec2, seg.epoch2, seg.distance2Pc, seg.radialVelocity2KmS) ?: continue
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
            val apparent = positionAt(star, stellarEpochYear)
            val p = project(apparent.first, apparent.second) ?: continue
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

        val visibleSatellites = sats.visible(cal, lat, lon)
        for (sat in visibleSatellites) {
            val trackPath = Path()
            var connected = false
            for (point in sat.track) {
                val projected = if (point.altDeg > -5.0) projectAltAz(point.azDeg, point.altDeg, -5.0) else null
                if (projected == null) {
                    connected = false
                } else if (!connected) {
                    trackPath.moveTo(projected[0], projected[1])
                    connected = true
                } else {
                    trackPath.lineTo(projected[0], projected[1])
                }
            }
            canvas.drawPath(trackPath, satelliteTrackPaint)
            val p = projectAltAz(sat.azDeg, sat.altDeg) ?: continue
            starPaint.color = 0xFF7FD6FF.toInt()
            starPaint.alpha = 255
            canvas.drawCircle(p[0], p[1], 3.2f * density, starPaint)
            if (Settings.showLabels(context)) {
                canvas.drawText(sat.name.substringBefore(" (").trim(), p[0] + 10f * density, p[1] - 8f * density, countPaint)
            }
        }

        // Reported observations are shown only when the selected date/time and observer match.
        // This is a direction marker; it does not imply a measured range or reconstructed track.
        for (marker in ufoSightings.visible(cal, lat, lon, Settings.skyAltitudeKm(context).toDouble())) {
            val p = projectAltAz(marker.azimuthDeg, marker.elevationDeg) ?: continue
            marker.sighting.angularUncertaintyDeg?.let { angularUncertainty ->
                val uncertaintyPx = (angularUncertainty / verticalFovDegrees * height).toFloat()
                    .coerceIn(5f * density, 70f * density)
                glowPaint.color = 0xFFFF6B5E.toInt()
                glowPaint.alpha = 34
                canvas.drawCircle(p[0], p[1], uncertaintyPx, glowPaint)
            }
            starPaint.color = 0xFFFF8A72.toInt()
            starPaint.alpha = 255
            canvas.drawCircle(p[0], p[1], 5f * density, starPaint)
            starPaint.style = Paint.Style.STROKE
            starPaint.strokeWidth = 1.5f * density
            canvas.drawCircle(p[0], p[1], 9f * density, starPaint)
            starPaint.style = Paint.Style.FILL
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

        for (naturalMoon in naturalMoonDirections(cal)) {
            val (alt, az) = SkyMath.toAltAz(naturalMoon.raDeg, naturalMoon.decDeg, lst, lat)
            val p = projectAltAz(az, alt, -5.0) ?: continue
            starPaint.color = 0xFFB9D7F2.toInt()
            starPaint.alpha = 235
            canvas.drawCircle(p[0], p[1], 2.2f * density, starPaint)
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

        CockpitOverlay.draw(canvas, width, height, density, Settings.cockpitOverlay(context))

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

        drawCompassStrip(canvas, cx)
        drawHoverLabel(canvas)
    }

    private fun drawHoverLabel(canvas: Canvas) {
        val label = hoverLabel ?: return
        if (!hoverX.isFinite() || !hoverY.isFinite()) return
        hoverPaint.textSize = 15f * density
        hoverPaint.typeface = android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL)
        val padX = 12f * density
        val padY = 8f * density
        val boxW = hoverPaint.measureText(label) + padX * 2
        val boxH = hoverPaint.textSize + padY * 2
        val left = (hoverX + 18f * density).coerceAtMost(width - boxW - 8f * density).coerceAtLeast(8f * density)
        val top = (hoverY + 18f * density).coerceAtMost(height - boxH - 8f * density).coerceAtLeast(8f * density)
        hoverPaint.color = 0xEE101827.toInt()
        hoverPaint.style = Paint.Style.FILL
        canvas.drawRoundRect(left, top, left + boxW, top + boxH, 7f * density, 7f * density, hoverPaint)
        hoverPaint.color = 0xFFF2B25C.toInt()
        canvas.drawText(label, left + padX, top + padY + hoverPaint.textSize * 0.82f, hoverPaint)
    }

    private fun drawCompassStrip(canvas: Canvas, cx: Float) {
        val directions = listOf(
            0.0 to "N", 45.0 to "NE", 90.0 to "E", 135.0 to "SE",
            180.0 to "S", 225.0 to "SW", 270.0 to "W", 315.0 to "NW"
        )
        val heading = cameraAzimuthDegrees()
        val mirrorSign = if (Settings.skyMirror(context)) -1f else 1f
        val y = height - 16f * density
        for ((az, label) in directions) {
            var delta = (az - heading + 540.0) % 360.0 - 180.0
            if (abs(delta) > 90.0) continue
            val x = cx + mirrorSign * (-delta / 90.0).toFloat() * cx
            if (x < 6f * density || x > width - 6f * density) continue
            val textWidth = compassPaint.measureText(label)
            canvas.drawText(label, x - textWidth / 2f, y, compassPaint)
        }
        val center = "${heading.toInt()}°"
        val textWidth = compassPaint.measureText(center)
        canvas.drawText(center, cx - textWidth / 2f, y - compassPaint.textSize * 1.1f, compassPaint)
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
        private const val PAN_SPEED_AZ = 65f
        private const val PAN_SPEED_ALT = 45f
        private const val JOYSTICK_DEADZONE = 0.12f
    }
}
