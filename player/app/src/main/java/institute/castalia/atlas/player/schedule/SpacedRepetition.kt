package institute.castalia.atlas.player.schedule

object SpacedRepetition {

    val cycleNights = listOf(0, 1, 2, 4, 6)
    const val EXPOSURES = 5

    fun due(plays: Int, nightsSinceFirst: Int): Boolean {
        if (plays <= 0) return true
        if (plays >= EXPOSURES) return false
        return nightsSinceFirst >= cycleNights[plays]
    }
}
