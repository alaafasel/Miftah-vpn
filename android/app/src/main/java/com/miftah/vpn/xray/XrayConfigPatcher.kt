package com.miftah.vpn.xray

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/**
 * Applies the only two client-side mutations allowed by the project document:
 *  - replace the {{UUID}} placeholder (defensive; the server already does it)
 *  - replace outbounds[tag=proxyfb].settings.servers[0].address
 *
 * Everything else in the admin-managed JSON stays untouched.
 */
object XrayConfigPatcher {
    private const val PROXY_TAG = "proxyfb"
    const val SOCKS_PORT = 10808

    fun patch(config: JsonObject, uuid: String?, proxyAddress: String?): JsonObject {
        var root = if (uuid.isNullOrBlank()) config else replaceUuid(config, uuid).jsonObject
        if (!proxyAddress.isNullOrBlank()) root = applyProxy(root, proxyAddress)
        return ensureLocalInbounds(root)
    }

    private fun replaceUuid(element: JsonElement, uuid: String): JsonElement = when (element) {
        is JsonPrimitive ->
            if (element.isString) JsonPrimitive(element.content.replace("{{UUID}}", uuid)) else element
        is JsonArray -> JsonArray(element.map { replaceUuid(it, uuid) })
        is JsonObject -> JsonObject(element.mapValues { (_, v) -> replaceUuid(v, uuid) })
    }

    private fun applyProxy(root: JsonObject, address: String): JsonObject {
        val outbounds = root["outbounds"] as? JsonArray ?: return root
        val patched = buildJsonArray {
            outbounds.forEach { element ->
                val obj = element as? JsonObject
                if (obj?.get("tag")?.jsonPrimitive?.content != PROXY_TAG) {
                    add(element)
                    return@forEach
                }
                val settings = obj["settings"] as? JsonObject ?: buildJsonObject {}
                val servers = (settings["servers"] as? JsonArray)?.toMutableList()
                    ?: mutableListOf(JsonObject(emptyMap()))
                val first = (servers.firstOrNull() as? JsonObject) ?: JsonObject(emptyMap())
                servers[0] = JsonObject(first + ("address" to JsonPrimitive(address)))
                val newSettings = JsonObject(settings + ("servers" to JsonArray(servers)))
                add(JsonObject(obj + ("settings" to newSettings)))
            }
        }
        return JsonObject(root + ("outbounds" to patched))
    }

    /** Guarantees a local SOCKS inbound that tun2socks can connect to. */
    private fun ensureLocalInbounds(root: JsonObject): JsonObject {
        val inbounds = (root["inbounds"] as? JsonArray)?.toMutableList() ?: mutableListOf()
        val hasSocks = inbounds.any { inbound ->
            val obj = inbound as? JsonObject
            obj?.get("protocol")?.jsonPrimitive?.content == "socks" &&
                obj["port"]?.jsonPrimitive?.content == SOCKS_PORT.toString()
        }
        if (!hasSocks) {
            inbounds.add(
                buildJsonObject {
                    put("tag", JsonPrimitive("miftah-socks"))
                    put("listen", JsonPrimitive("127.0.0.1"))
                    put("port", JsonPrimitive(SOCKS_PORT))
                    put("protocol", JsonPrimitive("socks"))
                    put(
                        "settings",
                        buildJsonObject {
                            put("auth", JsonPrimitive("noauth"))
                            put("udp", JsonPrimitive(true))
                        },
                    )
                },
            )
        }
        return JsonObject(root + ("inbounds" to JsonArray(inbounds)))
    }
}
