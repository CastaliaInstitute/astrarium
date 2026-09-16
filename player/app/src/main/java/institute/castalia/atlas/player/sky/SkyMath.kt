package institute.castalia.atlas.player.sky

import java.util.Calendar
import kotlin.math.PI
import kotlin.math.acos
import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sin

object SkyMath {

    fun lstDeg(cal: Calendar, lonDeg: Double): Double {
        val jd = julianDay(cal)
        val d = jd - 2451545.0
        val lst = 280.46061837 + 360.98564736629 * d + lonDeg
        return ((lst % 360.0) + 360.0) % 360.0
    }

    fun julianDay(cal: Calendar): Double {
        val utc = Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"))
        utc.timeInMillis = cal.timeInMillis
        var y = utc.get(Calendar.YEAR).toDouble()
        var m = utc.get(Calendar.MONTH).toDouble() + 1
        val d = utc.get(Calendar.DAY_OF_MONTH).toDouble()
        val hours = utc.get(Calendar.HOUR_OF_DAY) + utc.get(Calendar.MINUTE) / 60.0 +
            utc.get(Calendar.SECOND) / 3600.0
        if (m <= 2) {
            y -= 1
            m += 12
        }
        val a = floor(y / 100)
        val b = 2 - a + floor(a / 4)
        return floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + b - 1524.5 + hours / 24.0
    }

    fun toAltAz(raDeg: Double, decDeg: Double, lstDeg: Double, latDeg: Double): Pair<Double, Double> {
        val ha = Math.toRadians(norm(lstDeg - raDeg))
        val dec = Math.toRadians(decDeg)
        val lat = Math.toRadians(latDeg)
        val sinAlt = sin(dec) * sin(lat) + cos(dec) * cos(lat) * cos(ha)
        val alt = asin(sinAlt.coerceIn(-1.0, 1.0))
        val cosAz = (sin(dec) - sin(alt) * sin(lat)) / (cos(alt) * cos(lat))
        var az = acos(cosAz.coerceIn(-1.0, 1.0))
        if (sin(ha) > 0) az = 2 * PI - az
        return Pair(Math.toDegrees(alt), Math.toDegrees(az))
    }

    fun norm(deg: Double): Double = ((deg % 360.0) + 360.0) % 360.0

    fun sunAltDeg(cal: Calendar, latDeg: Double, lonDeg: Double): Double {
        val n = julianDay(cal) - 2451545.0
        val L = 280.460 + 0.9856474 * n
        val g = Math.toRadians(357.528 + 0.9856003 * n)
        val lambda = Math.toRadians(L + 1.915 * sin(g) + 0.020 * sin(2 * g))
        val eps = Math.toRadians(23.439 - 0.0000004 * n)
        val ra = atan2(cos(eps) * sin(lambda), cos(lambda))
        val dec = asin(sin(eps) * sin(lambda))
        val ha = Math.toRadians(lstDeg(cal, lonDeg)) - ra
        val lat = Math.toRadians(latDeg)
        return Math.toDegrees(asin(sin(lat) * sin(dec) + cos(lat) * cos(dec) * cos(ha)))
    }

    fun nextDawnMs(cal: Calendar, latDeg: Double, lonDeg: Double): Long {
        var t = cal.timeInMillis + 30 * 60_000L
        var prev = sunAltDeg(Calendar.getInstance().apply { timeInMillis = t }, latDeg, lonDeg)
        for (i in 1..160) {
            t += 10 * 60_000L
            val c = Calendar.getInstance().apply { timeInMillis = t }
            val a = sunAltDeg(c, latDeg, lonDeg)
            if (prev < -18.0 && a >= -18.0) return t
            prev = a
        }
        return cal.timeInMillis + 8 * 3600_000L
    }

    fun galacticPlane(): List<Pair<Double, Double>> {
        val m = doubleArrayOf(
            -0.0549, -0.8734, -0.4838,
            0.4941, -0.4448, 0.7470,
            -0.8677, -0.1981, 0.4560
        )
        val pts = ArrayList<Pair<Double, Double>>(73)
        for (i in 0..72) {
            val l = Math.toRadians(i * 5.0)
            val gx = cos(l)
            val gy = sin(l)
            val ex = m[0] * gx + m[3] * gy
            val ey = m[1] * gx + m[4] * gy
            val ez = m[2] * gx + m[5] * gy
            val dec = asin(ez.coerceIn(-1.0, 1.0))
            val ra = kotlin.math.atan2(ey, ex)
            pts.add(Pair(norm(Math.toDegrees(ra)), Math.toDegrees(dec)))
        }
        return pts
    }
}
