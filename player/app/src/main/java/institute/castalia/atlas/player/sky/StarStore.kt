package institute.castalia.atlas.player.sky

import android.content.Context
import android.util.Log
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.PriorityQueue
import java.util.concurrent.ConcurrentHashMap
import kotlin.concurrent.thread

/**
 * Astrarium tile client: fetches Gaia catalog tiles from the local Atlas star
 * server (or, later, the public site), with a bounded RAM LRU and disk LRU.
 *
 * Tile kinds mirror the server contract:
 *   space/{level}/{morton}  12-byte 3D records
 *   shell/{level}/{zone}    8-byte 2D records
 *   sky/{level}/{zone}      12-byte sky-ordered records (bright levels)
 */
class StarStore(private val ctx: Context, private val baseUrl: String) {

    companion object {
        const val RAM_BUDGET = 48 * 1024 * 1024      // 48 MB of decoded tile bytes
        const val DISK_BUDGET = 512L * 1024 * 1024   // persistent cache cap
        const val LEVELS = 12
        const val PC_BOX = 8192.0
        const val OCT_DEPTH = 8
        const val CELL_EDGE = 2.0 * PC_BOX / (1 shl OCT_DEPTH)
        private fun morton(x: Int, y: Int, z: Int): Long {
            fun spread(v: Int): Long {
                var v = v.toLong() and 0xFF
                v = (v or (v shl 8)) and 0x00FF00FF
                v = (v or (v shl 4)) and 0x0F0F0F0F
                v = (v or (v shl 2)) and 0x33333333
                v = (v or (v shl 1)) and 0x55555555
                return v
            }
            return spread(x) or (spread(y) shl 1) or (spread(z) shl 2)
        }

        /** Octree cell key containing (pc) coordinates. */
        fun cellKey(px: Double, py: Double, pz: Double): Long {
            val n = (1 shl OCT_DEPTH) - 1
            val x = (((px + PC_BOX) / (2.0 * PC_BOX)) * (1 shl OCT_DEPTH)).toInt().coerceIn(0, n)
            val y = (((py + PC_BOX) / (2.0 * PC_BOX)) * (1 shl OCT_DEPTH)).toInt().coerceIn(0, n)
            val z = (((pz + PC_BOX) / (2.0 * PC_BOX)) * (1 shl OCT_DEPTH)).toInt().coerceIn(0, n)
            return morton(x, y, z)
        }

        /** Decoded star: x, y, z (pc), mag (G), color (BP-RP). */
        fun decode3D(bytes: ByteArray): Array<FloatArray> {
            val n = bytes.size / 12
            val out = Array(5) { FloatArray(n) }
            var b = 0
            for (i in 0 until n) {
                fun u16(off: Int): Int =
                    (bytes[b + off].toInt() and 0xFF) or ((bytes[b + off + 1].toInt() and 0xFF) shl 8)
                fun s8(off: Int): Int = bytes[b + off].toInt()
                out[0][i] = u16(0) / 65535f
                out[1][i] = u16(2) / 65535f
                out[2][i] = u16(4) / 65535f
                out[3][i] = u16(6) / 100f
                out[4][i] = (bytes[b + 8].toInt() and 0xFF) / 50f - 128f / 50f
                b += 12
            }
            return out
        }
    }

    private class Entry(val key: String, val bytes: ByteArray, var lastUse: Long)

    private val ram = LinkedHashMap<String, Entry>(256, 0.75f, true)
    private var ramBytes = 0
    private val diskDir: File by lazy {
        File(ctx.cacheDir, "astrarium-tiles").apply { mkdirs() }
    }
    private val inFlight = ConcurrentHashMap<String, Boolean>()
    private val pending = java.util.PriorityQueue<Pair<Long, String>>(11, compareBy { it.first })
    private val lock = Object()
    @Volatile
    var tileHits = 0
        private set
    @Volatile
    var tileMisses = 0
        private set

    init {
        thread(name = "starstore") {
            android.util.Log.d("StarStore", "worker started")
            while (true) {
                val key: String = synchronized(lock) {
                    if (pending.isEmpty()) {
                        lock.wait()
                        ""
                    } else pending.poll().second
                }
                if (key.isEmpty()) continue
android.util.Log.d("StarStore", "popped $key")
                if (get(key) != null) {
                    inFlight.remove(key)
                    continue
                }
                val bytes = fetchHttp(key)
                if (bytes != null) {
                    put(key, bytes)
                    tileHits++
                } else {
                    tileMisses++
                    inFlight.remove(key)   // allow retry when the tile appears server-side
                }
            }
        }
    }

    /** Queue a tile if not cached. key = "space/L3/12345". */
    fun request(key: String, priority: Long) {
        synchronized(lock) {
            if (inFlight.putIfAbsent(key, true) == null) {
                pending.add(Pair(priority, key))
                android.util.Log.d("StarStore", "queued $key")
                lock.notifyAll()
            }
        }
    }

    /** Fetch tile bytes (RAM → disk → triggers background fetch). Null while pending. */
    fun get(key: String): ByteArray? {
        synchronized(ram) {
            ram[key]?.let { it.lastUse = System.currentTimeMillis(); return it.bytes }
        }
        val df = File(diskDir, key.replace('/', '_'))
        if (df.exists()) {
            val b = df.readBytes()
            put(key, b)
            return b
        }
        return null
    }

    private fun put(key: String, bytes: ByteArray) {
        synchronized(ram) {
            ram[key] = Entry(key, bytes, System.currentTimeMillis())
            ramBytes += bytes.size
            val it = ram.entries.iterator()
            while (ramBytes > RAM_BUDGET && it.hasNext()) {
                val e = it.next()
                ramBytes -= e.value.bytes.size
                it.remove()
            }
        }
        val df = File(diskDir, key.replace('/', '_'))
        if (!df.exists()) {
            try { df.writeBytes(bytes) } catch (_: Exception) {}
        }
        pruneDisk()
    }

    private fun pruneDisk() {
        thread(name = "starstore-prune") {
            try {
                val files = diskDir.listFiles() ?: return@thread
                var total = files.sumOf { it.length() }
                if (total <= DISK_BUDGET) return@thread
                val sorted = files.sortedBy { it.lastModified() }
                for (f in sorted) {
                    if (total <= DISK_BUDGET) break
                    total -= f.length()
                    f.delete()
                }
            } catch (_: Exception) {}
        }
    }

    private fun fetchHttp(key: String): ByteArray? {
        return try {
            val url = URL("$baseUrl/api/v1/tiles/$key")
            val c = url.openConnection() as HttpURLConnection
            c.connectTimeout = 3000
            c.readTimeout = 8000
            if (c.responseCode != 200) {
                c.disconnect()
                return null
            }
            c.inputStream.use { ins ->
                val out = ByteArrayOutputStream()
                val buf = ByteArray(8192)
                while (true) {
                    val n = ins.read(buf)
                    if (n < 0) break
                    out.write(buf, 0, n)
                }
                out.toByteArray()
            }.also { c.disconnect() }
        } catch (e: Exception) {
            Log.w("StarStore", "fetch $key: ${e.message}")
            null
        }
    }
}
