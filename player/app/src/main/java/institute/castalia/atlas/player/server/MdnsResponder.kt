package institute.castalia.atlas.player.server

import android.content.Context
import android.net.wifi.WifiManager
import java.io.ByteArrayOutputStream
import java.net.DatagramPacket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.MulticastSocket
import java.net.NetworkInterface
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import kotlin.concurrent.thread

class MdnsResponder(private val advertisedPort: Int) {

    private companion object {
        const val GROUP = "224.0.0.251"
        const val PORT = 5353
        const val HOST_NAME = "astrarium.local"
        const val WWW_NAME = "www.astrarium.local"
        const val INSTANCE_FQDN = "Astrarium._http._tcp.local"
        const val TYPE_FQDN = "_http._tcp.local"
        const val SERVICES_FQDN = "_services._dns-sd._udp.local"
        const val TTL = 120
    }

    private data class Q(val name: String, val qtype: Int, val qclass: Int)

    @Volatile
    private var running = false
    private var sock: MulticastSocket? = null
    private var lock: WifiManager.MulticastLock? = null
    private var ipBytes: ByteArray = ByteArray(4)

    fun start(ctx: Context) {
        if (running) return
        running = true
        try {
            ipBytes = findIp()
        } catch (_: Exception) {
            ipBytes = ByteArray(4)
        }
        try {
            val wm = ctx.getSystemService(Context.WIFI_SERVICE) as WifiManager
            lock = wm.createMulticastLock("astrarium")
            lock?.setReferenceCounted(false)
            lock?.acquire()
        } catch (_: Exception) {
        }
        thread(name = "mdns") {
            var socket: MulticastSocket? = null
            val joined = mutableListOf<NetworkInterface>()
            try {
                socket = MulticastSocket(null)
                socket.reuseAddress = true
                socket.bind(InetSocketAddress("0.0.0.0", PORT))
                val group = InetAddress.getByName(GROUP)
                for (nif in java.util.Collections.list(NetworkInterface.getNetworkInterfaces())) {
                    if (!nif.isUp || nif.isLoopback) continue
                    try {
                        socket.joinGroup(InetSocketAddress(group, 0), nif)
                        joined.add(nif)
                        android.util.Log.i("Mdns", "joined $GROUP on ${nif.name}")
                    } catch (e: Exception) {
                        android.util.Log.w("Mdns", "join ${nif.name}: ${e.message}")
                    }
                }
                if (joined.isEmpty()) throw IllegalStateException("no multicast-capable interface")
                socket.soTimeout = 300
                sock = socket
                announce(socket, 4)
                val buf = ByteArray(2048)
                while (running) {
                    try {
                        val p = DatagramPacket(buf, buf.size)
                        socket.receive(p)
                        if (buf.size >= 12 && p.length > 12) {
                            val reply = handleQuery(buf.copyOfRange(0, p.length), p.address, p.port)
                            if (reply != null) {
                                socket.send(DatagramPacket(reply, reply.size, p.address, p.port))
                            }
                        }
                    } catch (_: SocketTimeoutException) {
                    } catch (_: Exception) {
                        if (!running) break
                    }
                }
            } catch (e: Exception) {
                android.util.Log.w("MdnsResponder", "failed: ${e.message}")
            } finally {
                runCatching {
                    for (nif in joined) socket?.leaveGroup(InetSocketAddress(InetAddress.getByName(GROUP), 0), nif)
                }
                runCatching { socket?.close() }
                sock = null
            }
        }
        android.util.Log.i("MdnsResponder", "advertising $HOST_NAME port $advertisedPort")
    }

    private fun findIp(): ByteArray {
        for (nif in java.util.Collections.list(NetworkInterface.getNetworkInterfaces())) {
            if (!nif.isUp || nif.isLoopback) continue
            for (addr in java.util.Collections.list(nif.inetAddresses)) {
                if (addr.isAnyLocalAddress || addr.isLinkLocalAddress || addr.isMulticastAddress) continue
                val raw = addr.address
                if (raw.size == 4) return raw
            }
        }
        return ByteArray(4)
    }

    private fun announce(sock: MulticastSocket, times: Int) {
        val payload = buildAdvert()
        val group = InetAddress.getByName(GROUP)
        for (i in 0 until times) {
            try {
                sock.send(DatagramPacket(payload, payload.size, group, PORT))
            } catch (_: Exception) {
            }
            try {
                Thread.sleep(700)
            } catch (_: Exception) {
            }
        }
    }

    private fun handleQuery(data: ByteArray, srcIp: InetAddress, srcPort: Int): ByteArray? {
        val flags = ((data[2].toInt() and 0xff) shl 8) or (data[3].toInt() and 0xff)
        if (flags and 0x8000 != 0) return null
        val qd = ((data[4].toInt() and 0xff) shl 8) or (data[5].toInt() and 0xff)
        if (qd == 0) return null
        var off = 12
        val questions = mutableListOf<Q>()
        for (i in 0 until qd) {
            val name = readName(data, off) ?: return null
            if (name.consumed < 0) return null
            off = name.end
            if (off + 4 > data.size) return null
            val qtype = ((data[off].toInt() and 0xff) shl 8) or (data[off + 1].toInt() and 0xff)
            val qclass = ((data[off + 2].toInt() and 0xff) shl 8) or (data[off + 3].toInt() and 0xff)
            questions.add(Q(name.text, qtype, qclass))
            off += 4
        }
        if (questions.isEmpty()) return null
        android.util.Log.i("Mdns", "query from ${srcIp.hostAddress}:${srcPort} ${questions.joinToString { "${it.name}/${it.qtype}" }}")

        val answers = ByteArrayOutputStream()
        var count = 0
        var answered = false
        for (q in questions) {
            val n = q.name.lowercase()
            val ok = q.qclass == 1 || q.qclass == 255
            val isHost = n == HOST_NAME || n == WWW_NAME
            when {
                isHost && ok && q.qtype == 28 -> {
                    // RFC 6762 negative response: NSEC asserting no AAAA exists
                    answers.write(nsecNoAaaa(n))
                    count++
                    answered = true
                }
                isHost && ok && (q.qtype == 1 || q.qtype == 255) -> {
                    answers.write(aRecord(n, ipBytes))
                    count++
                    answered = true
                }
                n == TYPE_FQDN && ok && (q.qtype == 12 || q.qtype == 255) -> {
                    answers.write(ptrRecord(TYPE_FQDN, INSTANCE_FQDN))
                    count++
                    answered = true
                }
                n == SERVICES_FQDN && ok && (q.qtype == 12 || q.qtype == 255) -> {
                    answers.write(ptrRecord(SERVICES_FQDN, TYPE_FQDN))
                    count++
                    answered = true
                }
                n == INSTANCE_FQDN.lowercase() && ok && (q.qtype == 33 || q.qtype == 255) -> {
                    answers.write(srvRecord(INSTANCE_FQDN, advertisedPort, HOST_NAME))
                    count++
                    answered = true
                }
                n == INSTANCE_FQDN.lowercase() && ok && (q.qtype == 16 || q.qtype == 255) -> {
                    answers.write(txtRecord(INSTANCE_FQDN))
                    count++
                    answered = true
                }
            }
        }
        if (!answered) return null

        val hdr = ByteBuffer.allocate(12)
        hdr.putShort(((data[0].toInt() and 0xff) shl 8 or (data[1].toInt() and 0xff)).toShort())
        hdr.putShort(0x8400.toShort())
        hdr.putShort(qd.toShort())
        hdr.putShort(count.toShort())
        hdr.putShort(0)
        hdr.putShort(0)
        val resp = ByteArrayOutputStream()
        resp.write(hdr.array())
        resp.write(data, 12, off - 12)
        resp.write(answers.toByteArray())
        return resp.toByteArray()
    }

    private fun buildAdvert(): ByteArray {
        val answers = ByteArrayOutputStream()
        answers.write(ptrRecord(SERVICES_FQDN, TYPE_FQDN))
        answers.write(ptrRecord(TYPE_FQDN, INSTANCE_FQDN))
        answers.write(srvRecord(INSTANCE_FQDN, advertisedPort, HOST_NAME))
        answers.write(txtRecord(INSTANCE_FQDN))
        answers.write(aRecord(HOST_NAME, ipBytes))
        answers.write(aRecord(WWW_NAME, ipBytes))
        val hdr = ByteBuffer.allocate(12)
        hdr.putShort(0)
        hdr.putShort(0x8400.toShort())
        hdr.putShort(0)
        hdr.putShort(6.toShort())
        hdr.putShort(0)
        hdr.putShort(0)
        val out = ByteArrayOutputStream()
        out.write(hdr.array())
        out.write(answers.toByteArray())
        return out.toByteArray()
    }

    private fun nameBytes(name: String): ByteArray {
        val out = ByteArrayOutputStream()
        for (part in name.split(".")) {
            out.write(part.length)
            out.write(part.toByteArray(Charsets.US_ASCII))
        }
        out.write(0)
        return out.toByteArray()
    }

    private fun rr(name: String, rtype: Int, rdata: ByteArray): ByteArray {
        val n = nameBytes(name)
        val hdr = ByteBuffer.allocate(10)
        hdr.putShort(rtype.toShort())
        // cache-flush bit (0x8001) on unique records so clients adopt new answers immediately
        hdr.putShort(0x8001.toShort())
        hdr.putInt(TTL)
        hdr.putShort(rdata.size.toShort())
        val out = ByteArrayOutputStream()
        out.write(n)
        out.write(hdr.array())
        out.write(rdata)
        return out.toByteArray()
    }

    private fun aRecord(name: String, ip: ByteArray): ByteArray = rr(name, 1, ip)

    private fun ptrRecord(name: String, target: String): ByteArray = rr(name, 12, nameBytes(target))

    private fun srvRecord(name: String, port: Int, target: String): ByteArray {
        val r = ByteBuffer.allocate(6 + 1 + target.length + 1)
        r.putShort(0)
        r.putShort(0)
        r.putShort(port.toShort())
        r.put(nameBytes(target))
        return rr(name, 33, r.array())
    }

    private fun txtRecord(name: String): ByteArray = rr(name, 16, byteArrayOf(0))

    private fun nsecNoAaaa(name: String): ByteArray {
        // NSEC rdata: owner name + window 0, bitmap len 6, asserting A(1), TXT(16), SRV(33), NSEC(47) exist — no AAAA
        val rd = ByteArrayOutputStream()
        rd.write(nameBytes(name))
        rd.write(0x00)
        rd.write(0x06)
        rd.write(0x40); rd.write(0x00); rd.write(0x80); rd.write(0x00)
        rd.write(0x40); rd.write(0x01)
        return rr(name, 47, rd.toByteArray())
    }

    private class NameResult(val text: String, val end: Int, val consumed: Int)

    private fun readName(data: ByteArray, start: Int): NameResult? {
        val labels = StringBuilder()
        var off = start
        var jumped = false
        var firstEnd = -1
        var steps = 0
        while (steps++ < 64) {
            if (off >= data.size) return null
            val len = data[off].toInt() and 0xff
            if (len == 0) {
                if (firstEnd < 0) firstEnd = off + 1
                break
            }
            if (len and 0xc0 == 0xc0) {
                if (off + 1 >= data.size) return null
                val ptr = ((len and 0x3f) shl 8) or (data[off + 1].toInt() and 0xff)
                if (!jumped) firstEnd = off + 2
                jumped = true
                off = ptr
                continue
            }
            if (len > 63) return null
            if (off + 1 + len > data.size) return null
            if (labels.isNotEmpty()) labels.append('.')
            for (i in 0 until len) labels.append((data[off + 1 + i].toInt() and 0xff).toChar())
            off += 1 + len
        }
        return NameResult(labels.toString(), if (firstEnd >= 0) firstEnd else off, off - start)
    }
}