package institute.castalia.atlas.player.server

import android.os.IBinder
import android.os.Parcel

/**
 * Raw binder client for the vendor GPIO service (softwinner.gpio, com.softwinner.IGpioService).
 *
 * Native service (libgpioservice.so, vendor/aw/homlet/framework/gpio/libgpio/IGpioService.cpp):
 *   onTransact:
 *     code 0: checkInterface, readCString(path)                 -> readData(path)            -> reply.writeInt32(ret)
 *     code 1: checkInterface, readCString(path), readInt32(len), readCString(data)
 *                                       -> writeData(data, len, path) -> reply.writeInt32(ret)
 *   writeData(buf, len, path): open(path, O_WRONLY); write(fd, buf, len); close
 *   readData(path): opens and reads an int from path
 *
 * Parcel.writeCString is not exposed to Java, so C-strings are emulated with
 * writeByteArray(bytes + NUL): Parcel::readCString scans until NUL, and byte
 * streams carry no alignment padding, so this reproduces the native layout.
 */
object GpioBinder {

    private const val SERVICE = "softwinner.gpio"
    private const val DESCRIPTOR = "com.softwinner.IGpioService"
    private const val CODE_READ = 0
    private const val CODE_WRITE = 1

    private fun binder(): IBinder? = try {
        val sm = Class.forName("android.os.ServiceManager")
        sm.getMethod("getService", String::class.java).invoke(null, SERVICE) as? IBinder
    } catch (e: Exception) {
        null
    }

    private fun Parcel.writeCString(s: String) {
        writeByteArray(s.toByteArray(Charsets.UTF_8) + 0)
    }

    /** Writes `value` (as UTF-8 bytes) to `path`, as root. Returns service return code, or null on binder failure. */
    fun write(path: String, value: String): Int? {
        val b = binder() ?: return null
        val data = Parcel.obtain()
        val reply = Parcel.obtain()
        return try {
            data.writeInterfaceToken(DESCRIPTOR)
            val bytes = value.toByteArray(Charsets.UTF_8)
            data.writeCString(path)
            data.writeInt(bytes.size)
            data.writeCString(value)
            b.transact(CODE_WRITE, data, reply, 0)
            reply.readInt()
        } catch (e: Exception) {
            null
        } finally {
            data.recycle()
            reply.recycle()
        }
    }

    /** Reads an int from `path`. Returns value, or null on binder failure. */
    fun read(path: String): Long? {
        val b = binder() ?: return null
        val data = Parcel.obtain()
        val reply = Parcel.obtain()
        return try {
            data.writeInterfaceToken(DESCRIPTOR)
            data.writeCString(path)
            b.transact(CODE_READ, data, reply, 0)
            reply.readInt().toLong() and 0xFFFFFFFFL
        } catch (e: Exception) {
            null
        } finally {
            data.recycle()
            reply.recycle()
        }
    }

    /**
     * Probe: tries codes 0-3 with several parcel layouts, transacting each and
     * reporting (code, layout, ret, replyHex). Caller checks side effects.
     */
    fun probe(token: String, path: String, value: String, code: Int, layout: Int): Pair<Int, String>? {
        val b = binder() ?: return null
        val data = Parcel.obtain()
        val reply = Parcel.obtain()
        return try {
            data.writeInterfaceToken(token)
            val v = value.toByteArray(Charsets.UTF_8)
            val p = path.toByteArray(Charsets.UTF_8)
            when (layout) {
                0 -> { // int(len), cstring(path), cstring(value)
                    data.writeInt(v.size); data.writeCString(path); data.writeCString(value)
                }
                1 -> { // int(len), cstring(value), cstring(path)
                    data.writeInt(v.size); data.writeCString(value); data.writeCString(path)
                }
                2 -> { // cstring(path), int(len), cstring(value)
                    data.writeCString(path); data.writeInt(v.size); data.writeCString(value)
                }
                3 -> { // cstring(path), cstring(value), int(len)
                    data.writeCString(path); data.writeCString(value); data.writeInt(v.size)
                }
                4 -> { // int(len), cstring(value), int(0)
                    data.writeInt(v.size); data.writeCString(value); data.writeInt(0)
                }
                5 -> { // int(len), string16(path), string16(value)
                    data.writeInt(v.size); data.writeString(path); data.writeString(value)
                }
                6 -> { // string16(path), string16(value)
                    data.writeString(path); data.writeString(value)
                }
                7 -> { // int(len), cstring(value)
                    data.writeInt(v.size); data.writeCString(value)
                }
            }
            b.transact(code, data, reply, 0)
            val hex = reply.marshall().joinToString("") { "%02x".format(it) }.take(64)
            val ret = try { reply.readInt() } catch (e: Exception) { Int.MIN_VALUE }
            Pair(ret, hex)
        } catch (e: Exception) {
            Pair(Int.MIN_VALUE, "EXC:${e.javaClass.simpleName}")
        } finally {
            data.recycle()
            reply.recycle()
        }
    }
}
