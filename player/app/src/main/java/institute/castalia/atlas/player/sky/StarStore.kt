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

    /** Local core tier: bootstrapped from Atlas into app-scoped external storage. */
    private val coreDir: File? by lazy {
        File(ctx.getExternalFilesDir(null), "astrarium-stars").apply { mkdirs() }
    }
    private val coreIndexes = HashMap<String, Pair<LongArray, IntArray>>() // level -> (keys, offsets)
    @Volatile
    var bootstrapped = false
        private set
    private var bootstrapStarted = false

    private fun bootstrapCore() {
        if (bootstrapStarted) return
        bootstrapStarted = true
        thread(name = "starstore-bootstrap") {
            val dir = coreDir ?: return@thread
            val needed = ArrayList<Pair<String, String>>()
            for (lvl in listOf("L0", "L1", "L2", "L3")) {
                for (f in listOf("space.bin", "space_index.bin", "sky.bin", "sky_index.bin", "shell.bin", "shell_index.bin")) {
                    if (!File(dir, "$lvl/$f").exists() || File(dir, "$lvl/$f").length() == 0L) {
                        needed.add(Pair(lvl, f))
                    }
                }
            }
            for ((lvl, f) in needed) {
                try {
                    val c = (URL("$baseUrl/api/v1/core/$lvl/$f").openConnection() as HttpURLConnection)
                    c.connectTimeout = 5000
                    c.readTimeout = 300000
                    if (c.responseCode == 200) {
                        val out = File(dir, "$lvl/$f")
                        out.parentFile?.mkdirs()
                        c.inputStream.use { ins -> out.outputStream().use { ins.copyTo(it) } }
                        Log.d("StarStore", "core $lvl/$f ${out.length()}B")
                    }
                    c.disconnect()
                } catch (e: Exception) {
                    Log.w("StarStore", "core $lvl/$f: ${e.message}")
                }
            }
            synchronized(coreIndexes) { coreIndexes.clear() }
            bootstrapped = true
            Log.d("StarStore", "core bootstrap done (${needed.size} files)")
        }
    }

    private fun coreTile(kind: String, level: String, key: Long): ByteArray? {
        if (kind != "space") return null
        val dir = coreDir ?: return null
        if (!File(dir, "$level/space_index.bin").exists()) return null
        val (keys, offs) = synchronized(coreIndexes) {
            coreIndexes.getOrPut(level) {
                val f = File(dir, "$level/space_index.bin")
                if (!f.exists()) return@getOrPut Pair(LongArray(0), IntArray(0))
                val raw = f.readBytes()
                val n = raw.size / 16
                val ks = LongArray(n)
                val os_ = IntArray(n)
                for (i in 0 until n) {
                    var k = 0L
                    for (b in 0 until 8) k = k or ((raw[i * 16 + b].toLong() and 0xFF) shl (8 * b))
                    ks[i] = k
                    os_[i] = ((raw[i * 16 + 8].toInt() and 0xFF) or ((raw[i * 16 + 9].toInt() and 0xFF) shl 8)
                        or ((raw[i * 16 + 10].toInt() and 0xFF) shl 16) or ((raw[i * 16 + 11].toInt() and 0xFF) shl 24))
                }
                Pair(ks, os_)
            }
        }
        var lo = 0
        var hi = keys.size - 1
        while (lo <= hi) {
            val mid = (lo + hi) ushr 1
            when {
                keys[mid] < key -> lo = mid + 1
                keys[mid] > key -> hi = mid - 1
                else -> {
                    val dataFile = File(dir, "$level/space.bin")
                    val count = if (mid + 1 < keys.size) offs[mid + 1] - offs[mid]
                    else (dataFile.length() - offs[mid]).toInt()
                    if (count <= 0) return null
                    val buf = ByteArray(count)
                    java.io.RandomAccessFile(dataFile, "r").use { raf ->
                        raf.seek(offs[mid].toLong())
                        raf.readFully(buf)
                    }
                    return buf
                }
            }
        }
        return null
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
        bootstrapCore()
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

    /** Fetch tile bytes (RAM → local core → disk cache → background HTTP). Null while pending. */
    fun get(key: String): ByteArray? {
        synchronized(ram) {
            ram[key]?.let { it.lastUse = System.currentTimeMillis(); return it.bytes }
        }
        val parts = key.split("/")
        if (parts.size == 3) {
            coreTile(parts[0], parts[1], parts[2].toLongOrNull() ?: 0L)?.let {
                put(key, it)
                return it
            }
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
