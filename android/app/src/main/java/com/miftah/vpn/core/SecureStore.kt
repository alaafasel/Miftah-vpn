package com.miftah.vpn.core

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Encrypted local storage for the device token and cached runtime config.
 * Keys are protected by Android Keystore (AES-256-GCM).
 */
class SecureStore(context: Context) {
    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "miftah_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun put(key: String, value: String) {
        prefs.edit().putString(key, value).apply()
    }

    fun get(key: String): String? = prefs.getString(key, null)

    fun remove(key: String) {
        prefs.edit().remove(key).apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        const val TOKEN = "device_token"
        const val CONFIG = "runtime_config"
        const val CONFIG_VERSION = "runtime_config_version"
        const val SELECTED_PROXY = "selected_proxy_id"
        const val PROXY_NAME = "selected_proxy_name"
        const val PROXY_ADDRESS = "selected_proxy_address"
    }
}
