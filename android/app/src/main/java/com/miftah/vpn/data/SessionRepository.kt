package com.miftah.vpn.data

import android.content.Context
import android.os.Build
import com.miftah.vpn.core.DeviceIdentity
import com.miftah.vpn.core.SecureStore
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject

class SessionRepository(context: Context, private val api: ApiClient) {
    private val store = SecureStore(context)
    private val json = Json { ignoreUnknownKeys = true }

    val hasToken: Boolean
        get() = !store.get(SecureStore.TOKEN).isNullOrBlank()

    init {
        api.token = store.get(SecureStore.TOKEN)
    }

    suspend fun activate(code: String): ActivateResponse {
        val response = api.activate(
            code = code.trim(),
            publicKey = DeviceIdentity.publicKeyBase64(),
            model = "${Build.MANUFACTURER} ${Build.MODEL}".trim(),
        )
        store.put(SecureStore.TOKEN, response.deviceToken)
        api.token = response.deviceToken
        return response
    }

    suspend fun status(): StatusResponse = api.status()

    suspend fun proxies(): List<ProxyItem> = api.proxies()

    suspend fun selectProxy(proxy: ProxyItem): SelectProxyResponse {
        val response = api.selectProxy(proxy.id)
        store.put(SecureStore.SELECTED_PROXY, response.selectedProxyId.toString())
        store.put(SecureStore.PROXY_NAME, response.name)
        store.put(SecureStore.PROXY_ADDRESS, response.address)
        return response
    }

    suspend fun config(): ConfigResponse {
        val response = api.config()
        store.put(SecureStore.CONFIG, response.config.toString())
        store.put(SecureStore.CONFIG_VERSION, response.version.toString())
        response.selectedProxyId?.let { store.put(SecureStore.SELECTED_PROXY, it.toString()) }
        return response
    }

    suspend fun configVersion(): Int = api.configVersion()

    suspend fun device(): DeviceInfo = api.device()

    suspend fun unbind() {
        api.unbind()
        clearSession()
    }

    fun cachedConfig(): JsonObject? {
        val raw = store.get(SecureStore.CONFIG) ?: return null
        return runCatching { json.parseToJsonElement(raw).let { it as JsonObject } }.getOrNull()
    }

    fun cachedConfigVersion(): Int = store.get(SecureStore.CONFIG_VERSION)?.toIntOrNull() ?: 0

    fun selectedProxyId(): Int? = store.get(SecureStore.SELECTED_PROXY)?.toIntOrNull()

    fun selectedProxyName(): String? = store.get(SecureStore.PROXY_NAME)

    fun selectedProxyAddress(): String? = store.get(SecureStore.PROXY_ADDRESS)

    fun clearSession() {
        store.clear()
        api.token = null
    }
}
