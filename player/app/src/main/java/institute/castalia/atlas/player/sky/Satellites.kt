package institute.castalia.atlas.player.sky

import android.content.Context
import java.util.Calendar
import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

data class SatMarker(val name: String, val azDeg: Double, val altDeg: Double)

class Satellites {

    private data class Tle(
        val name: String,
        val epochJ2000Days: Double,
        val n0RevPerDay: Double,
        val incDeg: Double,
        val raanDeg: Double,
        val argpDeg: Double,
        val maDeg: Double
    )

    private val sats = ArrayList<Tle>()

    fun load(ctx: Context) {
        try {
            val lines = ctx.assets.open("sky/satellites.tle").bufferedReader().readLines()
            var i = 0
            while (i + 2 <= lines.size) {
                if (lines[i].isNotBlank() && lines[i + 1].startsWith("1 ") && lines[i + 2].startsWith("2 ")) {
                    val tle = parse(lines[i].trim(), lines[i + 1], lines[i + 2])
                    if (tle != null) sats.add(tle)
                }
                i += 3
            }
        } catch (e: Exception) {
        }
    }

    fun visible(cal: Calendar, latDeg: Double, lonDeg: Double): List<SatMarker> {
        val sunAlt = SkyMath.sunAltDeg(cal, latDeg, lonDeg)
        if (sunAlt > -6.0) return emptyList()
        val out = ArrayList<SatMarker>()
        for (t in sats) {
            val m = propagate(t, cal, latDeg, lonDeg) ?: continue
            if (m.altDeg > 10.0) out.add(m)
        }
        return out
    }

    private fun parse(name: String, l1: String, l2: String): Tle? {
        return try {
            val yy = l1.substring(18, 20).trim().toInt()
            val year = if (yy < 57) 2000 + yy else 1900 + yy
            val doy = l1.substring(20, 32).trim().toDouble()
            val epoch = SkyMath.julianDay(y2kCal(year)) + (doy - 1.0) - 2451545.0
            val n0 = l1.substring(52, 63).trim().toDouble()
            val inc = l2.substring(8, 16).trim().toDouble()
            val raan = l2.substring(17, 25).trim().toDouble()
            val ecc = ("0." + l2.substring(26, 33).trim()).toDouble()
            val argp = l2.substring(34, 42).trim().toDouble()
            val ma = l2.substring(43, 51).trim().toDouble()
            Tle(name, epoch, n0, inc, raan, argp, ma).also {
                if (ecc > 0.05) null
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun y2kCal(year: Int): Calendar =
        Calendar.getInstance().apply { clear(); set(year, 0, 1, 0, 0, 0) }

    private fun propagate(t: Tle, cal: Calendar, latDeg: Double, lonDeg: Double): SatMarker? {
        val nowDays = SkyMath.julianDay(cal) - 2451545.0
        val dtSec = (nowDays - t.epochJ2000Days) * 86400.0
        if (kotlin.math.abs(dtSec) > 60.0 * 86400.0) return null
        val n = t.n0RevPerDay * 2.0 * Math.PI / 86400.0
        val a = (GM / (n * n)).pow(1.0 / 3.0)
        val ma = SkyMath.norm(t.maDeg + Math.toDegrees(n) * dtSec / 86400.0)
        val u = Math.toRadians(SkyMath.norm(t.argpDeg + ma))
        val inc = Math.toRadians(t.incDeg)
        val raan = Math.toRadians(t.raanDeg)
        val r = a
        val x = r * (cos(raan) * cos(u) - sin(raan) * sin(u) * cos(inc))
        val y = r * (sin(raan) * cos(u) + cos(raan) * sin(u) * cos(inc))
        val z = r * (sin(u) * sin(inc))
        val gst = Math.toRadians(SkyMath.lstDeg(cal, 0.0))
        val ra = atan2(y, x)
        val dec = asin((z / r).coerceIn(-1.0, 1.0))
        val lat = Math.toDegrees(dec)
        val lon = SkyMath.norm(Math.toDegrees(ra) - Math.toDegrees(gst)).let { if (it > 180.0) it - 360.0 else it }
        val altKm = r - EARTH_R

        val latR = Math.toRadians(latDeg)
        val lonR = Math.toRadians(lonDeg)
        val latS = Math.toRadians(lat)
        val lonS = Math.toRadians(lon)
        val e = (altKm + EARTH_R) * cos(latS) * sin(lonS - lonR)
        val nn = (altKm + EARTH_R) * (cos(latR) * sin(latS) - sin(latR) * cos(latS) * cos(lonS - lonR))
        val up = (altKm + EARTH_R) * (sin(latR) * sin(latS) + cos(latR) * cos(latS) * cos(lonS - lonR)) - EARTH_R
        val dist = sqrt(e * e + nn * nn + up * up)
        val el = Math.toDegrees(asin((up / dist).coerceIn(-1.0, 1.0)))
        val az = SkyMath.norm(Math.toDegrees(atan2(e, nn)))
        return SatMarker(t.name.trim(), az, el)
    }

    companion object {
        private const val GM = 398600.4418
        private const val EARTH_R = 6371.0
    }
}
