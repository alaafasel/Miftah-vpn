package com.miftah.vpn.core

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PublicKey
import java.security.spec.ECGenParameterSpec

/**
 * Hardware-backed device identity.
 *
 * A non-exportable EC P-256 key is generated inside Android Keystore. Only the
 * public key ever leaves the device; the server stores its SHA-256 fingerprint
 * and binds the license to it. No IMEI / ANDROID_ID is used.
 */
object DeviceIdentity {
    private const val ALIAS = "miftah_device_key"
    private const val PROVIDER = "AndroidKeyStore"

    @Synchronized
    fun publicKeyBase64(): String {
        val keyStore = KeyStore.getInstance(PROVIDER).apply { load(null) }
        val entry = keyStore.getEntry(ALIAS, null) as? KeyStore.PrivateKeyEntry
        val publicKey = entry?.certificate?.publicKey ?: generate()
        return Base64.encodeToString(publicKey.encoded, Base64.NO_WRAP)
    }

    private fun generate(): PublicKey {
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            PROVIDER,
        )
        generator.initialize(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY,
            )
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setUserAuthenticationRequired(false)
                .build(),
        )
        return generator.generateKeyPair().public
    }
}
