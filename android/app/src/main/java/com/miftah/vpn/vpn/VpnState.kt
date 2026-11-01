package com.miftah.vpn.vpn

import kotlinx.coroutines.flow.MutableStateFlow

object VpnState {
    val connected = MutableStateFlow(false)
    val connecting = MutableStateFlow(false)
    val lastError = MutableStateFlow<String?>(null)
}
