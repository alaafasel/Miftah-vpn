package com.miftah.vpn.ui.screens

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Public
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.miftah.vpn.ui.UiState
import com.miftah.vpn.ui.formatDate
import com.miftah.vpn.ui.remainingDays
import com.miftah.vpn.ui.theme.Danger
import com.miftah.vpn.ui.theme.Emerald
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.SurfaceNavy2
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted

@Composable
fun HomeScreen(
    state: UiState,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit,
    onRefresh: () -> Unit,
) {
    val connected = state.connected
    val connecting = state.connecting
    val days = remainingDays(state.status?.remainingSeconds ?: 0L)
    val active = state.status?.valid == true

    val ringColor by animateColorAsState(
        targetValue = when {
            connected -> Emerald
            connecting -> Gold
            else -> Gold.copy(alpha = 0.55f)
        },
        label = "ring",
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
    ) {
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            BrandRow(modifier = Modifier.weight(1f))
            IconButton(onClick = onRefresh, enabled = !state.busy) {
                if (state.busy) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = Gold,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(Icons.Filled.Refresh, contentDescription = "تحديث", tint = Gold)
                }
            }
        }

        Spacer(Modifier.height(26.dp))

        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Box(
                modifier = Modifier
                    .size(196.dp)
                    .background(
                        Brush.radialGradient(
                            listOf(
                                ringColor.copy(alpha = 0.18f),
                                Color.Transparent,
                            ),
                        ),
                        CircleShape,
                    )
                    .border(3.dp, ringColor, CircleShape)
                    .clickable(enabled = !connecting) {
                        if (connected) onDisconnect() else onConnect()
                    },
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = if (connected) Icons.Filled.Shield else Icons.Filled.PowerSettingsNew,
                        contentDescription = null,
                        tint = ringColor,
                        modifier = Modifier.size(52.dp),
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        text = when {
                            connecting -> "جارٍ الاتصال…"
                            connected -> "فصل"
                            else -> "اتصال"
                        },
                        color = TextMain,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }

        Spacer(Modifier.height(16.dp))
        Text(
            text = when {
                connecting -> "جارٍ الاتصال…"
                connected -> "متصل"
                else -> "غير متصل"
            },
            color = ringColor,
            fontSize = 15.sp,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(4.dp))
        Text(
            text = if (connected) "حركة المرور تمر عبر ${state.selectedProxyName ?: "MIFTAH"}"
            else "اضغط على الزر لبدء الاتصال",
            color = TextMuted,
            fontSize = 12.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )

        ErrorBanner(state.vpnError ?: state.error)

        Spacer(Modifier.height(22.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SectionCard(modifier = Modifier.weight(1f)) {
                Text("المتبقي", color = TextMuted, fontSize = 12.sp)
                Spacer(Modifier.height(6.dp))
                Text(
                    text = if (active) "$days" else "0",
                    color = if (active) Gold else Danger,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(text = "يوم", color = TextMuted, fontSize = 12.sp)
            }
            SectionCard(modifier = Modifier.weight(1f)) {
                Text("الترخيص", color = TextMuted, fontSize = 12.sp)
                Spacer(Modifier.height(10.dp))
                StatusPill(
                    text = if (active) "نشط" else "منتهي",
                    color = if (active) Emerald else Danger,
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = if (active) "ينتهي ${formatDate(state.status?.endsAt)}" else "جدّد الاشتراك",
                    color = TextMuted,
                    fontSize = 11.sp,
                )
            }
        }

        Spacer(Modifier.height(12.dp))

        SectionCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .background(SurfaceNavy2, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Filled.Public, contentDescription = null, tint = Gold, modifier = Modifier.size(20.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text("البروكسي المحدد", color = TextMuted, fontSize = 12.sp)
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = state.selectedProxyName ?: "لم يتم اختيار بروكسي",
                        color = TextMain,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
                Text(
                    text = "الإصدار ${state.configVersion}",
                    color = TextMuted,
                    fontSize = 11.sp,
                )
            }
        }

        Spacer(Modifier.height(24.dp))
    }
}
