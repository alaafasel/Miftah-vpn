package com.miftah.vpn.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.miftah.vpn.BuildConfig
import com.miftah.vpn.data.ApiClient
import com.miftah.vpn.data.ApiException
import com.miftah.vpn.data.ConfigResponse
import com.miftah.vpn.data.DeviceInfo
import com.miftah.vpn.data.ProxyItem
import com.miftah.vpn.data.SessionRepository
import com.miftah.vpn.data.StatusResponse
import com.miftah.vpn.vpn.VpnState
import com.miftah.vpn.xray.XrayConfigPatcher
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class Phase { Loading, Activation, Ready, Error }

data class UiState(
    val phase: Phase = Phase.Loading,
    val busy: Boolean = false,
    val error: String? = null,
    val status: StatusResponse? = null,
    val proxies: List<ProxyItem> = emptyList(),
    val selectedProxyId: Int? = null,
    val selectedProxyName: String? = null,
    val configVersion: Int = 0,
    val device: DeviceInfo? = null,
    val connected: Boolean = false,
    val connecting: Boolean = false,
    val vpnError: String? = null,
)

class AppViewModel(app: Application) : AndroidViewModel(app) {
    private val api = ApiClient(BuildConfig.API_BASE_URL)
    private val repo = SessionRepository(app, api)

    private val _state = MutableStateFlow(UiState())
    val state = _state.asStateFlow()

    init {
        viewModelScope.launch {
            VpnState.connected.collect { c -> _state.update { it.copy(connected = c) } }
        }
        viewModelScope.launch {
            VpnState.connecting.collect { c -> _state.update { it.copy(connecting = c) } }
        }
        viewModelScope.launch {
            VpnState.lastError.collect { e -> _state.update { it.copy(vpnError = e) } }
        }
        bootstrap()
    }

    fun bootstrap() {
        viewModelScope.launch {
            _state.update { it.copy(phase = Phase.Loading, error = null) }
            if (!repo.hasToken) {
                _state.update { it.copy(phase = Phase.Activation) }
                return@launch
            }
            try {
                val status = repo.status()
                val proxies = repo.proxies()
                val config = repo.config()
                val device = repo.device()
                applyReady(status, proxies, config, device)
            } catch (e: ApiException) {
                if (e.status == 401 || e.status == 403) {
                    repo.clearSession()
                    _state.update { it.copy(phase = Phase.Activation) }
                } else {
                    _state.update { it.copy(phase = Phase.Error, error = e.message) }
                }
            } catch (e: Exception) {
                _state.update { it.copy(phase = Phase.Error, error = e.message) }
            }
        }
    }

    private fun applyReady(
        status: StatusResponse,
        proxies: List<ProxyItem>,
        config: ConfigResponse,
        device: DeviceInfo?,
    ) {
        val selectedId = config.selectedProxyId ?: status.selectedProxyId ?: repo.selectedProxyId()
        val selected = proxies.firstOrNull { it.id == selectedId }
        _state.update {
            it.copy(
                phase = Phase.Ready,
                busy = false,
                error = null,
                status = status,
                proxies = proxies,
                selectedProxyId = selectedId,
                selectedProxyName = selected?.name ?: repo.selectedProxyName(),
                configVersion = config.version,
                device = device,
            )
        }
    }

    fun activate(code: String) {
        if (code.isBlank()) {
            _state.update { it.copy(error = "أدخل كود التفعيل") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                repo.activate(code)
                bootstrap()
            } catch (e: ApiException) {
                _state.update { it.copy(busy = false, error = friendly(e)) }
            } catch (e: Exception) {
                _state.update { it.copy(busy = false, error = e.message ?: "خطأ غير متوقع") }
            }
        }
    }

    fun selectProxy(proxy: ProxyItem) {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                repo.selectProxy(proxy)
                _state.update {
                    it.copy(
                        busy = false,
                        selectedProxyId = proxy.id,
                        selectedProxyName = proxy.name,
                        proxies = it.proxies.map { p -> p.copy(selected = p.id == proxy.id) },
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(busy = false, error = e.message) }
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                val status = repo.status()
                val proxies = repo.proxies()
                val remoteVersion = repo.configVersion()
                val config = if (remoteVersion != repo.cachedConfigVersion()) {
                    repo.config()
                } else {
                    ConfigResponse(
                        version = remoteVersion,
                        config = repo.cachedConfig() ?: repo.config().config,
                        selectedProxyId = status.selectedProxyId,
                    )
                }
                val device = repo.device()
                applyReady(status, proxies, config, device)
            } catch (e: Exception) {
                _state.update { it.copy(busy = false, error = e.message) }
            }
        }
    }

    fun unbind() {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                repo.unbind()
                _state.update { UiState(phase = Phase.Activation) }
            } catch (e: Exception) {
                _state.update { it.copy(busy = false, error = e.message) }
            }
        }
    }

    fun clearVpnError() = _state.update { it.copy(vpnError = null) }

    fun setVpnError(message: String) = _state.update { it.copy(vpnError = message) }

    fun onVpnDenied() = _state.update { it.copy(vpnError = "تم رفض إذن VPN") }

    /** Builds the final runtime JSON (proxy applied) and returns it with the proxy name. */
    suspend fun buildRuntimeConfig(): Pair<String, String>? {
        val cached = repo.cachedConfig() ?: runCatching { repo.config().config }.getOrNull()
            ?: return null
        val patched = XrayConfigPatcher.patch(
            cached,
            uuid = null,
            proxyAddress = repo.selectedProxyAddress(),
        )
        return patched.toString() to (repo.selectedProxyName() ?: "MIFTAH")
    }

    private fun friendly(e: ApiException): String = when (e.status) {
        403 -> "الكود غير صالح أو الاشتراك منتهٍ"
        409 -> "هذا الكود مرتبط بجهاز آخر"
        429 -> "محاولات كثيرة، انتظر قليلاً"
        0 -> "تعذر الاتصال بالسيرفر"
        else -> e.message
    }
}
