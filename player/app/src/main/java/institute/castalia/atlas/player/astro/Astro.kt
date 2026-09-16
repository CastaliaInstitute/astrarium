package institute.castalia.atlas.player.astro

import institute.castalia.atlas.player.sky.MoonInfo
import institute.castalia.atlas.player.sky.SolarSystem
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.cos

data class BodyPos(val name: String, val lonDeg: Double, val sign: String)
data class Aspect(val a: String, val b: String, val type: String, val orbDeg: Double)
data class AstroSnapshot(
    val sun: BodyPos,
    val moon: BodyPos,
    val moonIllum: Double,
    val moonPhase: String,
    val planets: List<BodyPos>,
    val aspects: List<Aspect>
)

object Astro {

    private val SIGNS = listOf(
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    )

    private val PHASES = listOf(
        "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
        "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"
    )

    private val ASPECTS = listOf(
        Triple("Conjunction", 0.0, 8.0),
        Triple("Sextile", 60.0, 4.0),
        Triple("Square", 90.0, 6.0),
        Triple("Trine", 120.0, 6.0),
        Triple("Opposition", 180.0, 8.0)
    )

    fun signOf(lonDeg: Double): String =
        SIGNS[((lonDeg % 360.0 + 360.0) % 360.0 / 30.0).toInt() % 12]

    fun snapshot(cal: Calendar): AstroSnapshot {
        val sunLon = SolarSystem.sunEclLon(cal)
        val moon: MoonInfo = SolarSystem.moon(cal)
        val bodies = ArrayList<BodyPos>()
        bodies.add(BodyPos("Sun", sunLon, signOf(sunLon)))
        bodies.add(BodyPos("Moon", moon.eclLon, signOf(moon.eclLon)))
        SolarSystem.planets(cal).forEach { p ->
            bodies.add(BodyPos(p.name, p.eclLon, signOf(p.eclLon)))
        }
        val planetsOnly = bodies.filter { it.name != "Sun" && it.name != "Moon" }
        val aspects = ArrayList<Aspect>()
        val aspectables = bodies
        for (i in aspectables.indices) {
            for (j in i + 1 until aspectables.size) {
                val a = aspectables[i]
                val b = aspectables[j]
                var sep = abs(a.lonDeg - b.lonDeg)
                if (sep > 180.0) sep = 360.0 - sep
                for ((type, angle, orb) in ASPECTS) {
                    val dev = abs(sep - angle)
                    val tight = if (a.name == "Moon" || b.name == "Moon") orb else orb * 0.7
                    if (dev <= tight) {
                        aspects.add(Aspect(a.name, b.name, type, dev))
                        break
                    }
                }
            }
        }
        val phaseIdx = ((moon.eclLon - sunLon + 360.0) % 360.0 / 45.0).toInt() % 8
        return AstroSnapshot(
            sun = bodies[0],
            moon = bodies[1],
            moonIllum = moon.illum,
            moonPhase = PHASES[phaseIdx],
            planets = planetsOnly,
            aspects = aspects.sortedBy { it.orbDeg }
        )
    }
}
