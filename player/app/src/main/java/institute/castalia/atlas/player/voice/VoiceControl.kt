package institute.castalia.atlas.player.voice

import android.content.Context
import institute.castalia.atlas.player.Settings
import institute.castalia.atlas.player.sleep.SleepGuide
import org.json.JSONObject

/**
 * Maps a spoken phrase (already transcribed by a client such as the Atlas
 * tablet or the parent PWA) to projector actions. Client does STT only;
 * intent parsing happens here so any client can POST /api/voice {text}.
 */
class VoiceControl(private val ctx: Context, private val sleepGuide: SleepGuide) {

    fun handle(raw: String): JSONObject {
        val text = raw.lowercase().trim()
        val r = when {
            matches(text, "wake up", "good morning", "im awake", "i'm awake", "wake") -> act("wake") { sleepGuide.wake() }

            matches(text, "wind down", "bedtime", "goodnight", "good night", "start sleep", "go to sleep", "time for bed") -> act("sleep-start") { sleepGuide.start() }

            matches(text, "show the stars", "show stars", "full screen stars", "stars please", "night sky") -> act("sky") { sleepGuide.skyNow() }

            matches(text, "launch", "take off", "blast off", "start the journey", "begin the journey") -> act("launch") { sleepGuide.skyNow() }

            matches(text, "release", "look away", "free view", "clear look", "stop looking") -> act("look-clear") { sleepGuide.clearLook() }

            text.startsWith("look at ") || text.startsWith("show me ") || text.startsWith("go to ") ||
                text.startsWith("find ") || text.startsWith("where is ") || text.startsWith("look for ") ->
                lookTarget(text)

            text.startsWith("course ") || text.startsWith("set course ") || text.startsWith("target ") ->
                course(text)

            matches(text, "lines on", "show lines", "constellation lines on", "turn lines on") -> act("lines-on") { sleepGuide.setConsLines(true) }
            matches(text, "lines off", "hide lines", "constellation lines off", "turn lines off") -> act("lines-off") { sleepGuide.setConsLines(false) }
            matches(text, "art on", "show art", "constellation art on", "turn art on", "show figures") -> act("art-on") { sleepGuide.setConsArt(true) }
            matches(text, "art off", "hide art", "constellation art off", "turn art off", "hide figures") -> act("art-off") { sleepGuide.setConsArt(false) }

            matches(text, "faster", "speed up", "more warp", "full speed", "warp nine") -> act("warp-up") {
                sleepGuide.setTimeScale((currentScale() * 2).coerceAtMost(1000f))
            }
            matches(text, "slower", "slow down", "less warp", "half speed") -> act("warp-down") {
                sleepGuide.setTimeScale((currentScale() / 2).coerceAtLeast(0.25f))
            }
            matches(text, "normal speed", "stop warping", "real time", "regular speed") -> act("warp-normal") { sleepGuide.setTimeScale(1f) }

            matches(text, "louder", "volume up", "turn it up") -> act("volume-up") { bumpVolume(+3) }
            matches(text, "quieter", "softer", "volume down", "turn it down") -> act("volume-down") { bumpVolume(-3) }

            matches(text, "brighter", "lights up", "turn up the lights") -> act("brighter") { bumpBrightness(1.5f) }
            matches(text, "dimmer", "darker", "lights down", "turn down the lights") -> act("dimmer") { bumpBrightness(2f / 3) }

            matches(text, "listen for waking", "start listening", "monitor on", "enable monitor") -> act("monitor-on") {
                Settings.setMonitorEnabled(ctx, true); sleepGuide.applyLiveSettings()
            }
            matches(text, "stop listening", "monitor off", "disable monitor") -> act("monitor-off") {
                Settings.setMonitorEnabled(ctx, false); sleepGuide.applyLiveSettings()
            }

            else -> JSONObject().put("ok", false).put("action", "none").put("text", raw)
        }
        return r.put("text", raw)
    }

    private fun currentScale(): Float =
        sleepGuide.telemetryJson().optDouble("timeScale", 1.0).toFloat()

    private fun matches(text: String, vararg phrases: String): Boolean =
        phrases.any { p -> Regex("\\b" + Regex.escape(p) + "\\b").containsMatchIn(text) }

    private fun act(action: String, body: () -> Unit): JSONObject =
        try {
            body()
            JSONObject().put("ok", true).put("action", action)
        } catch (e: Exception) {
            JSONObject().put("ok", false).put("action", action).put("error", e.toString())
        }

    private fun lookTarget(text: String): JSONObject {
        val t = text
            .removePrefix("look at ").removePrefix("show me ").removePrefix("go to ")
            .removePrefix("find ").removePrefix("where is ").removePrefix("look for ")
            .trim()
        if (t.isBlank()) return JSONObject().put("ok", false).put("action", "look")
        return try {
            if (sleepGuide.lookAtStar(t) || sleepGuide.lookAtCons(t))
                JSONObject().put("ok", true).put("action", "look").put("target", t)
            else
                JSONObject().put("ok", false).put("action", "look").put("error", "unknown target")
        } catch (e: Exception) {
            JSONObject().put("ok", false).put("action", "look").put("error", e.toString())
        }
    }

    private fun course(text: String): JSONObject {
        val t = text
            .removePrefix("set course ").removePrefix("course ")
            .removePrefix("target ").removePrefix("to ")
            .trim()
        if (t.isBlank()) return JSONObject().put("ok", false).put("action", "course")
        return try {
            sleepGuide.setCourse(t)
            JSONObject().put("ok", true).put("action", "course").put("target", t)
        } catch (e: Exception) {
            JSONObject().put("ok", false).put("action", "course").put("error", e.toString())
        }
    }

    private fun bumpVolume(delta: Int) {
        val v = (Settings.speakerVolume(ctx) + delta).coerceIn(1, 20)
        Settings.setSpeakerVolume(ctx, v)
        sleepGuide.applyLiveSettings()
    }

    private fun bumpBrightness(factor: Float) {
        val v = (Settings.nightBrightness(ctx) * factor).coerceIn(0.02f, 0.6f)
        Settings.setNightBrightness(ctx, v)
        sleepGuide.applyLiveSettings()
    }
}
