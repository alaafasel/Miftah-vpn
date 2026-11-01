package com.miftah.vpn.vpn

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import androidx.core.app.NotificationCompat
import com.miftah.vpn.MiftahApp
import com.miftah.vpn.R
import com.miftah.vpn.ui.MainActivity
import com.miftah.vpn.xray.Tun2Socks
import com.miftah.vpn.xray.XrayConfigPatcher
import com.miftah.vpn.xray.XrayCore
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import java.io.File

class MiftahVpnService : VpnService() {

    private var tun: ParcelFileDescriptor? = null
    private val json = Json { ignoreUnknownKeys = true }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startTunnel(
                intent.getStringExtra(EXTRA_CONFIG),
                intent.getStringExtra(EXTRA_PROXY_NAME) ?: "MIFTAH",
            )
            ACTION_STOP -> stopTunnel()
        }
        return START_NOT_STICKY
    }

    private fun startTunnel(configJson: String?, proxyName: String) {
        if (VpnState.connected.value) return
        VpnState.connecting.value = true
        VpnState.lastError.value = null
        startForeground(NOTIFICATION_ID, buildNotification(proxyName, connecting = true))
        try {
            require(!configJson.isNullOrBlank()) { "empty runtime config" }
            val config = json.parseToJsonElement(configJson).jsonObject
            val builder = Builder()
                .setSession("MIFTAH VPN")
                .setMtu(1500)
                .addAddress("10.111.222.1", 32)
                .addRoute("0.0.0.0", 0)
                .addDnsServer("1.1.1.1")
                .addDnsServer("8.8.8.8")
                .setBlocking(true)
            // Keep the app's own sockets outside the tunnel to avoid a routing loop.
            runCatching { builder.addDisallowedApplication(packageName) }
            val pfd = builder.establish() ?: error("VPN permission not granted")
            tun = pfd

            val configFile = File(filesDir, "runtime-config.json")
            configFile.writeText(config.toString())

            XrayCore.run(configFile.absolutePath)
            val rc = Tun2Socks.start(pfd.fd, XrayConfigPatcher.SOCKS_PORT, "1.1.1.1")
            check(rc == 0) { "tun2socks failed with code $rc" }

            VpnState.connected.value = true
            getSystemService(NotificationManager::class.java)
                .notify(NOTIFICATION_ID, buildNotification(proxyName, connecting = false))
        } catch (e: Exception) {
            VpnState.lastError.value = e.message ?: e.javaClass.simpleName
            stopTunnel()
        } finally {
            VpnState.connecting.value = false
        }
    }

    private fun stopTunnel() {
        runCatching { Tun2Socks.stop() }
        runCatching { XrayCore.stop() }
        runCatching { tun?.close() }
        tun = null
        VpnState.connected.value = false
        VpnState.connecting.value = false
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onRevoke() {
        stopTunnel()
        super.onRevoke()
    }

    override fun onDestroy() {
        stopTunnel()
        super.onDestroy()
    }

    private fun buildNotification(proxyName: String, connecting: Boolean): Notification {
        val open = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val text = if (connecting) getString(R.string.status_connecting)
        else getString(R.string.notif_text, proxyName)
        return NotificationCompat.Builder(this, MiftahApp.CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_key)
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(text)
            .setContentIntent(open)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    companion object {
        const val ACTION_START = "com.miftah.vpn.START"
        const val ACTION_STOP = "com.miftah.vpn.STOP"
        const val EXTRA_CONFIG = "config"
        const val EXTRA_PROXY_NAME = "proxy_name"
        private const val NOTIFICATION_ID = 1001
    }
}
