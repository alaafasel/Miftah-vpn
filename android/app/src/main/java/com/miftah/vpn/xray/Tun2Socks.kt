package com.miftah.vpn.xray

/**
 * JNI bridge to the bundled hev-socks5-tunnel build (`libmiftah-tun.so`).
 * See native/build-native.sh.
 */
object Tun2Socks {
    @Volatile
    private var loaded = false

    @Synchronized
    fun start(tunFd: Int, socksPort: Int, dns: String): Int {
        ensureLoaded()
        return nativeStart(tunFd, socksPort, dns)
    }

    fun stop() {
        if (loaded) runCatching { nativeStop() }
    }

    private fun ensureLoaded() {
        if (!loaded) {
            System.loadLibrary("miftah-tun")
            loaded = true
        }
    }

    private external fun nativeStart(tunFd: Int, socksPort: Int, dns: String): Int
    private external fun nativeStop()
}
