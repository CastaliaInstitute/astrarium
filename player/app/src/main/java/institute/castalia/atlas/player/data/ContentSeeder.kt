package institute.castalia.atlas.player.data

import android.content.Context
import org.json.JSONObject
import java.io.File

class ContentSeeder(private val ctx: Context, private val db: AppDatabase) {

    fun sync() {
        val raw = ctx.assets.open("content/manifest.json").bufferedReader().readText()
        val arr = JSONObject(raw).getJSONArray("lessons")
        val dir = File(ctx.filesDir, "lessons")
        dir.mkdirs()
        val rows = (0 until arr.length()).map { i ->
            val l = arr.getJSONObject(i)
            val fileName = l.getString("filePath").substringAfterLast('/')
            val out = File(dir, fileName)
            ctx.assets.open("content/$fileName").use { input ->
                out.outputStream().use { input.copyTo(it) }
            }
            Lesson(
                id = l.getLong("id"),
                title = l.getString("title"),
                band = l.getInt("band"),
                subject = l.getString("subject"),
                filePath = "file://" + out.absolutePath,
                durationSec = l.getInt("durationSec")
            )
        }
        db.runInTransaction { db.lessons().upsertAll(rows) }
    }
}
