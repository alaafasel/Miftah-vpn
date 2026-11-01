package com.miftah.vpn.xray

import java.lang.reflect.Method
import java.lang.reflect.Modifier

/**
 * Thin wrapper around the Xray-core gomobile library.
 *
 * The AAR is not committed to the repository; build it with
 * `native/build-native.sh` and place `libXray.aar` in `app/libs/`.
 * Reflection keeps the app compiling before the AAR exists and reports a
 * clear runtime error instead of crashing.
 *
 * Two naming schemes are accepted:
 *  - `libXray.Xray`          (XTLS/libXray prebuilt AAR)
 *  - `xraymobile.Xraymobile` (our own gomobile bind, see native/xraymobile)
 */
object XrayCore {
    private val CLASS_CANDIDATES = listOf(
        "libXray.Xray",
        "xraymobile.Xraymobile",
        "com.miftah.xray.Xray",
    )
    private val LIB_CANDIDATES = listOf("Xray", "xray", "gojni")

    private var clazz: Class<*>? = null
    private var loadError: String? = null

    @Synchronized
    fun isAvailable(): Boolean {
        if (clazz != null) return true
        if (loadError != null) return false
        var last: Throwable? = null
        for (lib in LIB_CANDIDATES) {
            runCatching { System.loadLibrary(lib) }.onFailure { last = it }
        }
        for (name in CLASS_CANDIDATES) {
            val found = runCatching { Class.forName(name) }.getOrNull()
            if (found != null) {
                clazz = found
                loadError = null
                return true
            }
        }
        loadError = last?.message ?: "missing libXray.aar (no Xray class found)"
        return false
    }

    fun loadError(): String? = loadError

    fun run(configPath: String): String {
        require(isAvailable()) { "Xray core not bundled: ${loadError ?: "missing libXray.aar"}" }
        val result = invoke("run", arrayOf<Any?>(configPath, ""))
            ?: invoke("run", arrayOf<Any?>(configPath))
        return result?.toString() ?: "started"
    }

    fun stop() {
        if (!isAvailable()) return
        runCatching { invoke("stop", emptyArray()) }
    }

    fun test(configPath: String): String {
        require(isAvailable()) { "Xray core not bundled" }
        val result = invoke("test", arrayOf<Any?>(configPath)) ?: return "ok"
        return result.toString()
    }

    private fun invoke(name: String, args: Array<Any?>): Any? {
        val type = clazz ?: return null
        val method: Method = type.methods.firstOrNull {
            it.name.equals(name, ignoreCase = true) && it.parameterTypes.size == args.size
        } ?: return null
        val receiver = if (Modifier.isStatic(method.modifiers)) {
            null
        } else {
            type.getDeclaredConstructor().newInstance()
        }
        return method.invoke(receiver, *args)
    }
}
