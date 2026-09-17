package institute.castalia.atlas.player

import android.content.Context

object Settings {

    private const val FILE = "atlas"
    private const val NIGHT_BRIGHTNESS = "night_brightness"
    private const val AMBER_ALPHA = "amber_alpha"
    private const val KIOSK = "kiosk"
    private const val BEDTIME = "bedtime_minutes"
    private const val SESSION_CAP = "session_cap_minutes"
    private const val MUSIC_MINUTES = "music_minutes"
    private const val FADE_MINUTES = "fade_minutes"
    private const val MONITOR_ENABLED = "monitor_enabled"
    private const val AROUSAL_THRESHOLD = "arousal_threshold"
    private const val SOOTHE_BRIGHTNESS = "soothe_brightness"
    private const val SKY_LAT = "sky_lat"
    private const val SKY_LON = "sky_lon"
    private const val SKY_BOTTOM_AZ = "sky_bottom_az"
    private const val SKY_DURING_MUSIC = "sky_during_music"
    private const val SKY_MODE = "sky_mode"
    private const val SKY_MAG_LIMIT = "sky_mag_limit"
    private const val SKY_MIRROR = "sky_mirror"
    private const val SPEAKER_VOLUME = "speaker_volume"
    private const val ACTIVE_BAND = "active_band"
    private const val NOCTURNE_ENABLED = "nocturne_enabled"
    private const val SHOW_LABELS = "show_labels"
    private const val LESSON_WINDOW = "lesson_window_minutes"
    private const val ALIGN_JSON = "align_json"

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun nightBrightness(ctx: Context): Float = prefs(ctx).getFloat(NIGHT_BRIGHTNESS, 0.08f)
    fun amberAlpha(ctx: Context): Int = prefs(ctx).getInt(AMBER_ALPHA, 14)
    fun kiosk(ctx: Context): Boolean = prefs(ctx).getBoolean(KIOSK, false)
    fun bedtimeMinutes(ctx: Context): Int = prefs(ctx).getInt(BEDTIME, 19 * 60 + 30)
    fun sessionCapMinutes(ctx: Context): Int = prefs(ctx).getInt(SESSION_CAP, 15)
    fun musicMinutes(ctx: Context): Int = prefs(ctx).getInt(MUSIC_MINUTES, 10)
    fun fadeMinutes(ctx: Context): Int = prefs(ctx).getInt(FADE_MINUTES, 5)
    fun monitorEnabled(ctx: Context): Boolean = prefs(ctx).getBoolean(MONITOR_ENABLED, true)
    fun arousalThreshold(ctx: Context): Float = prefs(ctx).getFloat(AROUSAL_THRESHOLD, 0.035f)
    fun sootheBrightness(ctx: Context): Float = prefs(ctx).getFloat(SOOTHE_BRIGHTNESS, 0.06f)
    fun skyLat(ctx: Context): Float = prefs(ctx).getFloat(SKY_LAT, 39.06f)
    fun skyLon(ctx: Context): Float = prefs(ctx).getFloat(SKY_LON, -104.87f)
    fun skyBottomAz(ctx: Context): Float = prefs(ctx).getFloat(SKY_BOTTOM_AZ, 180f)
    fun skyDuringMusic(ctx: Context): Boolean = prefs(ctx).getBoolean(SKY_DURING_MUSIC, true)
    fun skyMode(ctx: Context): String = prefs(ctx).getString(SKY_MODE, "tour") ?: "tour"
    fun skyMagLimit(ctx: Context): Float = prefs(ctx).getFloat(SKY_MAG_LIMIT, 5.5f)
    fun skyMirror(ctx: Context): Boolean = prefs(ctx).getBoolean(SKY_MIRROR, true)
    fun speakerVolume(ctx: Context): Int = prefs(ctx).getInt(SPEAKER_VOLUME, 10)
    fun activeBand(ctx: Context): Int = prefs(ctx).getInt(ACTIVE_BAND, 0)
    fun nocturneEnabled(ctx: Context): Boolean = prefs(ctx).getBoolean(NOCTURNE_ENABLED, true)
    fun showLabels(ctx: Context): Boolean = prefs(ctx).getBoolean(SHOW_LABELS, false)
    fun lessonWindowMinutes(ctx: Context): Int = prefs(ctx).getInt(LESSON_WINDOW, 120)

    fun lessonWindowOpen(ctx: Context, nowMinutes: Int): Boolean {
        val delta = ((nowMinutes - bedtimeMinutes(ctx)) + 1440) % 1440
        return delta <= lessonWindowMinutes(ctx)
    }

    fun setNightBrightness(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(NIGHT_BRIGHTNESS, v.coerceIn(0.02f, 0.6f)).apply()

    fun setAmberAlpha(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(AMBER_ALPHA, v.coerceIn(0, 120)).apply()

    fun setKiosk(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(KIOSK, v).apply()

    fun setBedtimeMinutes(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(BEDTIME, v.coerceIn(0, 23 * 60 + 59)).apply()

    fun setSessionCapMinutes(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(SESSION_CAP, v.coerceIn(5, 30)).apply()

    fun setMusicMinutes(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(MUSIC_MINUTES, v.coerceIn(1, 30)).apply()

    fun setFadeMinutes(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(FADE_MINUTES, v.coerceIn(1, 15)).apply()

    fun setMonitorEnabled(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(MONITOR_ENABLED, v).apply()

    fun setArousalThreshold(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(AROUSAL_THRESHOLD, v.coerceIn(0.01f, 0.2f)).apply()

    fun setSootheBrightness(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(SOOTHE_BRIGHTNESS, v.coerceIn(0.02f, 0.3f)).apply()

    fun setSkyLat(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(SKY_LAT, v.coerceIn(-89f, 89f)).apply()

    fun setSkyLon(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(SKY_LON, v.coerceIn(-180f, 180f)).apply()

    fun setSkyBottomAz(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(SKY_BOTTOM_AZ, v.coerceIn(0f, 359f)).apply()

    fun setSkyDuringMusic(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(SKY_DURING_MUSIC, v).apply()

    fun setSkyMode(ctx: Context, v: String) =
        prefs(ctx).edit().putString(SKY_MODE, if (v == "journey") "journey" else "tour").apply()

    fun setNocturneEnabled(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(NOCTURNE_ENABLED, v).apply()

    fun setSkyMagLimit(ctx: Context, v: Float) =
        prefs(ctx).edit().putFloat(SKY_MAG_LIMIT, v.coerceIn(3.5f, 6.5f)).apply()

    fun setSkyMirror(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(SKY_MIRROR, v).apply()

    fun setSpeakerVolume(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(SPEAKER_VOLUME, v.coerceIn(0, 20)).apply()

    fun setActiveBand(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(ACTIVE_BAND, v.coerceIn(0, 1)).apply()

    fun setShowLabels(ctx: Context, v: Boolean) =
        prefs(ctx).edit().putBoolean(SHOW_LABELS, v).apply()

    fun setLessonWindowMinutes(ctx: Context, v: Int) =
        prefs(ctx).edit().putInt(LESSON_WINDOW, v.coerceIn(0, 12 * 60)).apply()

    fun alignJson(ctx: Context): String = prefs(ctx).getString(ALIGN_JSON, "") ?: ""
    fun setAlignJson(ctx: Context, v: String) =
        prefs(ctx).edit().putString(ALIGN_JSON, v).apply()
}
