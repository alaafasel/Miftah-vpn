package com.miftah.vpn.ui

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.VpnService
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Public
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.miftah.vpn.ui.screens.AccountScreen
import com.miftah.vpn.ui.screens.ActivationScreen
import com.miftah.vpn.ui.screens.HomeScreen
import com.miftah.vpn.ui.screens.LogoMark
import com.miftah.vpn.ui.screens.ProxiesScreen
import com.miftah.vpn.ui.screens.ScreenBackground
import com.miftah.vpn.ui.screens.SplashScreen
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.Navy
import com.miftah.vpn.ui.theme.SurfaceNavy
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted
import com.miftah.vpn.vpn.MiftahVpnService
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            com.miftah.vpn.ui.theme.MiftahTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = Navy) {
                    MiftahRoot()
                }
            }
        }
    }
}

@Composable
private fun MiftahRoot(vm: AppViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()

    when (state.phase) {
        Phase.Loading -> SplashScreen()
        Phase.Activation -> ActivationScreen(
            busy = state.busy,
            error = state.error,
            onActivate = vm::activate,
        )
        Phase.Error -> ErrorScreen(state.error) { vm.bootstrap() }
        Phase.Ready -> ReadyContent(state, vm)
    }
}

@Composable
private fun ReadyContent(state: UiState, vm: AppViewModel) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var pendingStart by remember { mutableStateOf(false) }

    val doStart: () -> Unit = {
        scope.launch {
            val pair = vm.buildRuntimeConfig()
            if (pair == null) {
                vm.setVpnError("لا يوجد إعداد متاح، اضغط تحديث ثم أعد المحاولة")
                return@launch
            }
            val intent = Intent(context, MiftahVpnService::class.java).apply {
                action = MiftahVpnService.ACTION_START
                putExtra(MiftahVpnService.EXTRA_CONFIG, pair.first)
                putExtra(MiftahVpnService.EXTRA_PROXY_NAME, pair.second)
            }
            ContextCompat.startForegroundService(context, intent)
        }
    }

    val vpnLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val ok = result.resultCode == Activity.RESULT_OK
        val wasPending = pendingStart
        pendingStart = false
        if (ok && wasPending) doStart() else vm.onVpnDenied()
    }

    val requestVpn: () -> Unit = {
        val prepare = VpnService.prepare(context)
        if (prepare != null) {
            pendingStart = true
            vpnLauncher.launch(prepare)
        } else {
            doStart()
        }
    }

    val notifLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { requestVpn() }

    val startVpn: () -> Unit = {
        val needsNotif = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        if (needsNotif) notifLauncher.launch(Manifest.permission.POST_NOTIFICATIONS) else requestVpn()
    }

    val stopVpn: () -> Unit = {
        context.startService(
            Intent(context, MiftahVpnService::class.java).apply {
                action = MiftahVpnService.ACTION_STOP
            },
        )
    }

    var tab by rememberSaveable { mutableIntStateOf(0) }

    Scaffold(
        containerColor = Navy,
        bottomBar = {
            NavigationBar(containerColor = SurfaceNavy, tonalElevation = 0.dp) {
                val colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = Gold,
                    selectedTextColor = Gold,
                    unselectedIconColor = TextMuted,
                    unselectedTextColor = TextMuted,
                    indicatorColor = Gold.copy(alpha = 0.16f),
                )
                NavigationBarItem(
                    selected = tab == 0,
                    onClick = { tab = 0 },
                    icon = { Icon(Icons.Filled.Home, contentDescription = null) },
                    label = { Text("الرئيسية", fontSize = 11.sp) },
                    colors = colors,
                )
                NavigationBarItem(
                    selected = tab == 1,
                    onClick = { tab = 1 },
                    icon = { Icon(Icons.Filled.Public, contentDescription = null) },
                    label = { Text("البروكسي", fontSize = 11.sp) },
                    colors = colors,
                )
                NavigationBarItem(
                    selected = tab == 2,
                    onClick = { tab = 2 },
                    icon = { Icon(Icons.Filled.Person, contentDescription = null) },
                    label = { Text("الحساب", fontSize = 11.sp) },
                    colors = colors,
                )
            }
        },
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            when (tab) {
                0 -> HomeScreen(
                    state = state,
                    onConnect = startVpn,
                    onDisconnect = stopVpn,
                    onRefresh = vm::refresh,
                )
                1 -> ProxiesScreen(
                    proxies = state.proxies,
                    selectedProxyId = state.selectedProxyId,
                    busy = state.busy,
                    onSelect = vm::selectProxy,
                )
                else -> AccountScreen(
                    state = state,
                    onUnbind = vm::unbind,
                )
            }
        }
    }
}

@Composable
private fun ErrorScreen(message: String?, onRetry: () -> Unit) {
    ScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            LogoMark(size = 80.dp)
            Spacer(Modifier.height(20.dp))
            Text(
                text = "تعذر الاتصال",
                color = TextMain,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = message ?: "حدث خطأ غير متوقع",
                color = TextMuted,
                fontSize = 13.sp,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(24.dp))
            Button(
                onClick = onRetry,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Gold,
                    contentColor = Navy,
                ),
            ) {
                Text("إعادة المحاولة", fontWeight = FontWeight.Bold)
            }
        }
    }
}
