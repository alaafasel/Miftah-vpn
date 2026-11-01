package com.miftah.vpn.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class ActivateRequest(
    val code: String,
    @SerialName("public_key") val publicKey: String,
    val model: String? = null,
)

@Serializable
data class SubscriptionInfo(
    @SerialName("starts_at") val startsAt: String,
    @SerialName("ends_at") val endsAt: String,
)

@Serializable
data class ActivateResponse(
    @SerialName("device_token") val deviceToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Long = 0,
    @SerialName("license_status") val licenseStatus: String,
    val subscription: SubscriptionInfo? = null,
)

@Serializable
data class StatusResponse(
    val valid: Boolean,
    @SerialName("license_status") val licenseStatus: String,
    @SerialName("starts_at") val startsAt: String,
    @SerialName("ends_at") val endsAt: String,
    @SerialName("remaining_seconds") val remainingSeconds: Long,
    @SerialName("uuid_id") val uuidId: Int? = null,
    @SerialName("selected_proxy_id") val selectedProxyId: Int? = null,
)

@Serializable
data class ProxyItem(
    val id: Int,
    val name: String,
    val address: String,
    val selected: Boolean = false,
)

@Serializable
data class ConfigResponse(
    val version: Int,
    val config: JsonObject,
    @SerialName("selected_proxy_id") val selectedProxyId: Int? = null,
)

@Serializable
data class VersionResponse(val version: Int)

@Serializable
data class DeviceInfo(
    val id: Int,
    val model: String? = null,
    val fingerprint: String,
    @SerialName("bound_at") val boundAt: String,
    @SerialName("last_seen_at") val lastSeenAt: String? = null,
    @SerialName("selected_proxy_id") val selectedProxyId: Int? = null,
)

@Serializable
data class SelectProxyRequest(@SerialName("proxy_id") val proxyId: Int)

@Serializable
data class SelectProxyResponse(
    @SerialName("selected_proxy_id") val selectedProxyId: Int,
    val name: String,
    val address: String,
)
