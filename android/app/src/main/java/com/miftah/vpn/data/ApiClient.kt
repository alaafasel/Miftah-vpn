package com.miftah.vpn.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class ApiException(val status: Int, override val message: String) : Exception(message)

class ApiClient(private val baseUrl: String) {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        explicitNulls = false
    }
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    private val mediaType = "application/json; charset=utf-8".toMediaType()

    @Volatile
    var token: String? = null

    suspend fun activate(code: String, publicKey: String, model: String?): ActivateResponse {
        val body = json.encodeToString(
            ActivateRequest.serializer(),
            ActivateRequest(code = code, publicKey = publicKey, model = model),
        )
        return json.decodeFromString(
            ActivateResponse.serializer(),
            request("POST", "/api/v1/licenses/activate", body, auth = false),
        )
    }

    suspend fun status(): StatusResponse = json.decodeFromString(
        StatusResponse.serializer(),
        request("POST", "/api/v1/licenses/verify", "{}"),
    )

    suspend fun refreshToken(): ActivateResponse = json.decodeFromString(
        ActivateResponse.serializer(),
        request("POST", "/api/v1/licenses/refresh", "{}"),
    )

    suspend fun proxies(): List<ProxyItem> = json.decodeFromString(
        kotlinx.serialization.builtins.ListSerializer(ProxyItem.serializer()),
        request("GET", "/api/v1/proxies"),
    )

    suspend fun selectProxy(proxyId: Int): SelectProxyResponse = json.decodeFromString(
        SelectProxyResponse.serializer(),
        request(
            "POST",
            "/api/v1/proxies/select",
            json.encodeToString(SelectProxyRequest.serializer(), SelectProxyRequest(proxyId)),
        ),
    )

    suspend fun config(): ConfigResponse = json.decodeFromString(
        ConfigResponse.serializer(),
        request("GET", "/api/v1/config/current"),
    )

    suspend fun configVersion(): Int = json.decodeFromString(
        VersionResponse.serializer(),
        request("GET", "/api/v1/config/version"),
    )

    suspend fun device(): DeviceInfo = json.decodeFromString(
        DeviceInfo.serializer(),
        request("GET", "/api/v1/devices/me"),
    )

    suspend fun unbind() {
        request("POST", "/api/v1/devices/unbind", "{}")
    }

    private suspend fun request(
        method: String,
        path: String,
        body: String? = null,
        auth: Boolean = true,
    ): String = withContext(Dispatchers.IO) {
        val builder = Request.Builder().url(baseUrl.trimEnd('/') + path)
        if (auth) token?.let { builder.header("Authorization", "Bearer $it") }
        when (method) {
            "GET" -> builder.get()
            "POST" -> builder.post((body ?: "{}").toRequestBody(mediaType))
            "PUT" -> builder.put((body ?: "{}").toRequestBody(mediaType))
            "DELETE" -> builder.delete()
            else -> throw IllegalArgumentException("unsupported method $method")
        }
        val response = try {
            client.newCall(builder.build()).execute()
        } catch (e: IOException) {
            throw ApiException(0, "network error: ${e.message}")
        }
        response.use { r ->
            val text = r.body?.string().orEmpty()
            if (!r.isSuccessful) {
                throw ApiException(r.code, extractError(text))
            }
            text
        }
    }

    private fun extractError(text: String): String {
        if (text.isBlank()) return "request failed"
        return try {
            val root = json.parseToJsonElement(text).jsonObject
            val detail = root["detail"]
            when {
                detail == null -> text.take(200)
                detail is JsonObject -> detail["error"]?.jsonPrimitive?.content ?: text.take(200)
                else -> detail.jsonPrimitive.content
            }
        } catch (e: Exception) {
            text.take(200)
        }
    }
}
