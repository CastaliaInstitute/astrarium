package institute.castalia.atlas.player

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import institute.castalia.atlas.player.audio.AudioMonitor
import institute.castalia.atlas.player.data.ContentSeeder
import institute.castalia.atlas.player.data.AppDatabase
import institute.castalia.atlas.player.server.ParentServer
import institute.castalia.atlas.player.sleep.SleepGuide
import institute.castalia.atlas.player.sky.SkyView
import institute.castalia.atlas.player.sky.StarField3D
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.concurrent.thread

class MainActivity : Activity() {

    private lateinit var db: AppDatabase
    private lateinit var player: ExoPlayer
    private lateinit var sleepGuide: SleepGuide
    private lateinit var monitor: AudioMonitor
    private lateinit var skyView: SkyView
    private lateinit var clock: TextView

    private val handler = Handler(Looper.getMainLooper())

    private val clockTick = object : Runnable {
        override fun run() {
            clock.visibility =
                if (sleepGuide.phase == SleepGuide.Phase.DARK) View.INVISIBLE else View.VISIBLE
            clock.text = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
            handler.postDelayed(this, 30_000L)
        }
    }

    private val skyTick = object : Runnable {
        override fun run() {
            if (skyView.visibility == View.VISIBLE) skyView.invalidate()
            handler.postDelayed(this, 2_000L)
        }
    }

    private val monitorSync = object : Runnable {
        override fun run() {
            monitor.watchFor = when (sleepGuide.phase) {
                SleepGuide.Phase.DARK -> AudioMonitor.WatchFor.DARK
                SleepGuide.Phase.SOOTHE -> AudioMonitor.WatchFor.SOOTHE
                else -> AudioMonitor.WatchFor.NONE
            }
            handler.postDelayed(this, 5_000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = FrameLayout(this)
        val playerView = PlayerView(this)
        root.addView(playerView, FrameLayout.LayoutParams(-1, -1))

        skyView = SkyView(this)
        skyView.visibility = View.INVISIBLE
        root.addView(skyView, FrameLayout.LayoutParams(-1, -1))

        val starField = StarField3D(this)
        starField.visibility = View.INVISIBLE
        root.addView(starField, FrameLayout.LayoutParams(-1, -1))

        val overlay = View(this)
        overlay.background = ColorDrawable(Color.argb(Settings.amberAlpha(this), 242, 178, 92))
        root.addView(overlay, FrameLayout.LayoutParams(-1, -1))

        clock = TextView(this).apply {
            setTextColor(0xFFF2B25C.toInt())
            textSize = 22f
            setPadding(0, 48, 48, 0)
        }
        root.addView(clock, FrameLayout.LayoutParams(-2, -2, Gravity.TOP or Gravity.END))
        setContentView(root)

        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, root).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        db = AppDatabase.get(this)
        player = ExoPlayer.Builder(this).build()
        playerView.player = player

        thread {
            ContentSeeder(this, db).sync()
        }

        sleepGuide = SleepGuide(this, window, overlay, skyView, starField, db, player) { phase ->
            runOnUiThread { onPhaseChanged(phase, playerView, starField) }
        }
        sleepGuide.beginClockWatch()
        handler.post(clockTick)
        handler.post(monitorSync)

        monitor = AudioMonitor(
            onLevel = { },
            onArousal = { sleepGuide.onArousal() },
            onCalm = { sleepGuide.onCalm() }
        )
        if (monitor.hasPermission(this)) {
            monitor.start()
        } else {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 1)
        }

        ParentServer.start(applicationContext, db, sleepGuide, monitor)

        if (Settings.kiosk(this)) startLockTask()
    }

    private fun onPhaseChanged(phase: SleepGuide.Phase, playerView: PlayerView, starField: StarField3D) {
        val journey = Settings.skyMode(this) == "journey"
        val showSky = !journey && Settings.skyDuringMusic(this) &&
            (phase == SleepGuide.Phase.MUSIC || phase == SleepGuide.Phase.FADE)
        val showJourney = (journey && (phase == SleepGuide.Phase.MUSIC || phase == SleepGuide.Phase.FADE)) ||
            phase == SleepGuide.Phase.JOURNEY
        playerView.visibility =
            if (showSky || showJourney) View.INVISIBLE else View.VISIBLE
        skyView.visibility = if (showSky) View.VISIBLE else View.INVISIBLE
        if (showJourney) {
            if (phase == SleepGuide.Phase.JOURNEY && !starField.isRunning) {
                starField.start()
            }
        } else {
            starField.stop()
        }
        starField.visibility = if (showJourney) View.VISIBLE else View.INVISIBLE
        skyView.animate().cancel()
        starField.animate().cancel()
        if (showSky) {
            if (phase == SleepGuide.Phase.FADE) {
                skyView.animate().alpha(0f)
                    .setDuration(Settings.fadeMinutes(this) * 60_000L).start()
            } else {
                skyView.alpha = 1f
            }
        }
        if (showJourney) {
            if (phase == SleepGuide.Phase.FADE) {
                starField.animate().alpha(0f)
                    .setDuration(Settings.fadeMinutes(this) * 60_000L).start()
            } else {
                starField.alpha = 1f
            }
        }
        clock.visibility =
            if (phase == SleepGuide.Phase.DARK || phase == SleepGuide.Phase.JOURNEY) View.INVISIBLE else View.VISIBLE
    }

    override fun onResume() {
        super.onResume()
        handler.post(skyTick)
    }

    override fun onPause() {
        handler.removeCallbacks(skyTick)
        super.onPause()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        if (requestCode == 1 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            monitor.start()
        }
    }

    override fun onDestroy() {
        monitor.stop()
        super.onDestroy()
    }
}
