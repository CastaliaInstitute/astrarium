package institute.castalia.atlas.player.sky

import java.util.Calendar
import kotlin.math.atan2
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.sqrt

data class MoonInfo(val raDeg: Double, val decDeg: Double, val illum: Double, val eclLon: Double)

data class PlanetInfo(val name: String, val raDeg: Double, val decDeg: Double, val color: Int, val eclLon: Double)

object SolarSystem {

    private fun rev(x: Double): Double = ((x % 360.0) + 360.0) % 360.0

    private fun kepler(mDeg: Double, e: Double): Double {
        var m = Math.toRadians(rev(mDeg))
        var ecc = e
        var ecc2 = e * e
        var ecc3 = ecc2 * e
        var delta = m + ecc3 * sin(2 * m) * 0.5 + ecc2 * sin(m) + ecc3 * sin(3 * m) * (3.0 / 8.0)
        var e1 = delta - (delta - ecc * sin(delta) - m) / (1 - ecc * cos(delta))
        repeat(3) {
            e1 = e1 - (e1 - ecc * sin(e1) - m) / (1 - ecc * cos(e1))
        }
        return e1
    }

    private fun sunPos(d: Double): Triple<Double, Double, Double> {
        val w = 282.9404 + 4.70935e-5 * d
        val e = 0.016709 - 1.151e-9 * d
        val m = rev(356.0470 + 0.9856002585 * d)
        val ec = kepler(m, e)
        val xv = cos(ec) - e
        val yv = sin(ec) * sqrt(1 - e * e)
        val v = Math.toDegrees(atan2(yv, xv))
        val r = hypot(xv, yv)
        val lon = rev(v + w)
        return Triple(lon, r, m)
    }

    private fun eclToEq(lonDeg: Double, latDeg: Double, d: Double): Pair<Double, Double> {
        val eps = Math.toRadians(23.4393 - 0.0000004 * d)
        val lon = Math.toRadians(lonDeg)
        val lat = Math.toRadians(latDeg)
        val xe = cos(lon) * cos(lat)
        val ye = sin(lon) * cos(lat)
        val ze = sin(lat)
        val ra = rev(Math.toDegrees(atan2(ye * cos(eps) - ze * sin(eps), xe)))
        val dec = Math.toDegrees(asin(ye * sin(eps) + ze * cos(eps)))
        return Pair(ra, dec)
    }

    private fun heliocentric(els: DoubleArray, d: Double): Triple<Double, Double, Double> {
        val n = els[0] + els[1] * d
        val inc = els[2]
        val w = els[3] + els[4] * d
        val a = els[5]
        val e = els[6]
        val m = els[7] + els[8] * d
        val ec = kepler(m, e)
        val xv = a * (cos(ec) - e)
        val yv = a * sqrt(1 - e * e) * sin(ec)
        val v = atan2(yv, xv)
        val r = hypot(xv, yv)
        val nr = Math.toRadians(n)
        val ir = Math.toRadians(inc)
        val u = Math.toRadians(v) + Math.toRadians(w)
        val xh = r * (cos(nr) * cos(u) - sin(nr) * sin(u) * cos(ir))
        val yh = r * (sin(nr) * cos(u) + cos(nr) * sin(u) * cos(ir))
        val zh = r * sin(u) * sin(ir)
        return Triple(xh, yh, zh)
    }

    fun moon(cal: Calendar): MoonInfo {
        val d = SkyMath.julianDay(cal) - 2451543.5
        val n = rev(125.1228 - 0.0529538083 * d)
        val w = rev(318.0634 + 0.1643573223 * d)
        val a = 60.2666
        val e = 0.054900
        val m = rev(115.3654 + 13.0649929509 * d)
        val ec = kepler(m, e)
        val xv = a * (cos(ec) - e)
        val yv = a * sqrt(1 - e * e) * sin(ec)
        val v = Math.toDegrees(atan2(yv, xv))
        val r = hypot(xv, yv)
        val nr = Math.toRadians(n)
        val ir = Math.toRadians(5.1454)
        val u = Math.toRadians(v) + Math.toRadians(w)
        var lon = rev(v + w + n)
        var lat = Math.toDegrees(asin(zOf(u, ir)))
        val ms = rev(356.0470 + 0.9856002585 * d)
        val ws = rev(282.9404 + 4.70935e-5 * d)
        val ls = rev(ms + ws)
        val lm = rev(n + w + m)
        val bigD = rev(lm - ls)
        val f = rev(n + w + m)
        lon += -1.274 * sin(Math.toRadians(m - 2 * bigD))
        lon += 0.658 * sin(Math.toRadians(2 * bigD))
        lon += -0.186 * sin(Math.toRadians(ms))
        lon += -0.114 * sin(Math.toRadians(2 * f))
        lon += 0.059 * sin(Math.toRadians(2 * m - 2 * bigD))
        lon += 0.057 * sin(Math.toRadians(m - 2 * bigD + ms))
        lon += 0.053 * sin(Math.toRadians(m + 2 * bigD))
        lon += 0.046 * sin(Math.toRadians(2 * bigD - ms))
        lon += 0.041 * sin(Math.toRadians(m - ms))
        lon += -0.035 * sin(Math.toRadians(bigD))
        lat += -0.173 * sin(Math.toRadians(f - 2 * bigD))
        lat += -0.055 * sin(Math.toRadians(m - f - 2 * bigD))
        lat += -0.046 * sin(Math.toRadians(m + f - 2 * bigD))
        lat += 0.033 * sin(Math.toRadians(f + 2 * bigD))
        val elong = rev(lon - ls)
        val illum = (1 - cos(Math.toRadians(elong))) / 2
        val (ra, dec) = eclToEq(lon, lat, d)
        return MoonInfo(ra, dec, illum, lon)
    }

    private fun zOf(u: Double, ir: Double): Double = sin(u) * sin(ir)

    fun sunEclLon(cal: Calendar): Double {
        val d = SkyMath.julianDay(cal) - 2451543.5
        return sunPos(d).first
    }

    fun sunEq(cal: Calendar): Pair<Double, Double> {
        val d = SkyMath.julianDay(cal) - 2451543.5
        val (lon, _, _) = sunPos(d)
        return eclToEq(lon, 0.0, d)
    }

    fun moonDistance(cal: Calendar): Double {
        val d = SkyMath.julianDay(cal) - 2451543.5
        val m = rev(115.3654 + 13.0649929509 * d)
        val e = 0.054900
        val a = 60.2666
        val ec = kepler(m, e)
        return a * (1 - e * cos(ec)) * 6371.0
    }

    fun planets(cal: Calendar): List<PlanetInfo> {
        val d = SkyMath.julianDay(cal) - 2451543.5
        val (sunLon, sunR, _) = sunPos(d)
        val xs = sunR * cos(Math.toRadians(sunLon))
        val ys = sunR * sin(Math.toRadians(sunLon))
        val defs = listOf(
            "Mercury" to doubleArrayOf(48.3313, 3.24587e-5, 7.0047, 29.1241, 1.01444e-5, 0.387098, 0.2056321, 168.6562, 4.0923344493),
            "Venus" to doubleArrayOf(76.6799, 2.46590e-5, 3.3946, 54.8910, 1.38374e-5, 0.723330, 0.006773188 - 1.302e-9, 48.0052, 1.6021306646),
            "Mars" to doubleArrayOf(49.5574, 2.11081e-5, 1.8497, 286.5016, 2.92961e-5, 1.523688, 0.0934052, 18.6021, 0.5240207766),
            "Jupiter" to doubleArrayOf(100.4542, 2.72068e-6, 1.3030, 273.8777, 1.64505e-5, 5.20256, 0.048498, 19.8950, 0.0830853001),
            "Saturn" to doubleArrayOf(113.6634, 2.38980e-6, 2.4886, 339.3939, 2.97661e-5, 9.55475, 0.055546, 316.9670, 0.0334442282)
        )
        val colors = mapOf(
            "Mercury" to 0xFFC9CDD4.toInt(),
            "Venus" to 0xFFF2E8C9.toInt(),
            "Mars" to 0xFFE07B5A.toInt(),
            "Jupiter" to 0xFFEAD9B0.toInt(),
            "Saturn" to 0xFFD9C48A.toInt()
        )
        val out = ArrayList<PlanetInfo>()
        for ((name, els) in defs) {
            val (xh, yh, zh) = heliocentric(els, d)
            val xg = xh + xs
            val yg = yh + ys
            val zg = zh
            val lon = Math.toDegrees(atan2(yg, xg))
            val lat = Math.toDegrees(atan2(zg, hypot(xg, yg)))
            val (ra, dec) = eclToEq(lon, lat, d)
            out.add(PlanetInfo(name, ra, dec, colors[name] ?: 0xFFFFFFFF.toInt(), lon))
        }
        return out
    }

    /** True geocentric distance of a planet in AU. */
    fun planetDistanceAu(name: String, cal: Calendar): Double {
        val d = SkyMath.julianDay(cal) - 2451543.5
        val (sunLon, sunR, _) = sunPos(d)
        val xs = sunR * cos(Math.toRadians(sunLon))
        val ys = sunR * sin(Math.toRadians(sunLon))
        val els = when (name) {
            "Mercury" -> doubleArrayOf(48.3313, 3.24587e-5, 7.0047, 29.1241, 1.01444e-5, 0.387098, 0.2056321, 168.6562, 4.0923344493)
            "Venus" -> doubleArrayOf(76.6799, 2.46590e-5, 3.3946, 54.8910, 1.38374e-5, 0.723330, 0.006773188 - 1.302e-9, 48.0052, 1.6021306646)
            "Mars" -> doubleArrayOf(49.5574, 2.11081e-5, 1.8497, 286.5016, 2.92961e-5, 1.523688, 0.0934052, 18.6021, 0.5240207766)
            "Jupiter" -> doubleArrayOf(100.4542, 2.72068e-6, 1.3030, 273.8777, 1.64505e-5, 5.20256, 0.048498, 19.8950, 0.0830853001)
            "Saturn" -> doubleArrayOf(113.6634, 2.38980e-6, 2.4886, 339.3939, 2.97661e-5, 9.55475, 0.055546, 316.9670, 0.0334442282)
            else -> return Double.NaN
        }
        val (xh, yh, zh) = heliocentric(els, d)
        return sqrt((xh + xs) * (xh + xs) + (yh + ys) * (yh + ys) + zh * zh)
    }
}
