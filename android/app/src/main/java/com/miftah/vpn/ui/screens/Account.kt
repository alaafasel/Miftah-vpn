package com.miftah.vpn.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.miftah.vpn.ui.UiState
import com.miftah.vpn.ui.formatDate
import com.miftah.vpn.ui.theme.Danger
import com.miftah.vpn.ui.theme.Emerald
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.SurfaceNavy
import com.miftah.vpn.ui.theme.SurfaceNavy2
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted

@Composable
fun AccountScreen(
    state: UiState,
    onUnbind: () -> Unit,
) {
    var confirmUnbind by remember { mutableStateOf(false) }
    val active = state.status?.valid == true

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
    ) {
        Spacer(Modifier.height(14.dp))
        Text(
            text = "الحساب",
            color = TextMain,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(16.dp))

        SectionCard {
            Text("حالة الاشتراك", color = TextMuted, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
            StatusPill(
                text = if (active) "نشط" else "غير نشط",
                color = if (active) Emerald else Danger,
            )
            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = SurfaceNavy2)
            Spacer(Modifier.height(6.dp))
            InfoRow("تاريخ التفعيل", formatDate(state.status?.startsAt))
            InfoRow("تاريخ الانتهاء", formatDate(state.status?.endsAt))
            InfoRow("البروكسي", state.selectedProxyName ?: "—")
            InfoRow("إصدار الإعداد", state.configVersion.toString())
        }

        Spacer(Modifier.height(12.dp))

        SectionCard {
            Text("معلومات الجهاز", color = TextMuted, fontSize = 12.sp)
            Spacer(Modifier.height(6.dp))
            InfoRow("الطراز", state.device?.model ?: "—")
            InfoRow("تاريخ الربط", formatDate(state.device?.boundAt))
            InfoRow("آخر ظهور", formatDate(state.device?.lastSeenAt))
            InfoRow(
                label = "بصمة المفتاح",
                value = state.device?.fingerprint?.take(16)?.plus("…") ?: "—",
                valueColor = TextMuted,
            )
        }

        Spacer(Modifier.height(12.dp))

        SectionCard {
            Text("إدارة الجهاز", color = TextMuted, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
            Text(
                text = "فك الارتباط يحرّر الكود من هذا الجهاز. ستحتاج إلى إعادة ربط من الإدارة أو كود جديد.",
                color = TextMuted,
                fontSize = 12.sp,
            )
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = { confirmUnbind = true },
                enabled = !state.busy,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Danger.copy(alpha = 0.16f),
                    contentColor = Danger,
                ),
            ) {
                Text("فك ارتباط الجهاز", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            }
        }

        ErrorBanner(state.error)
        Spacer(Modifier.height(24.dp))
    }

    if (confirmUnbind) {
        AlertDialog(
            onDismissRequest = { confirmUnbind = false },
            containerColor = SurfaceNavy,
            title = { Text("تأكيد فك الارتباط", color = TextMain) },
            text = {
                Text(
                    "سيتم تحرير هذا الجهاز من الكود. هل تريد المتابعة؟",
                    color = TextMuted,
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirmUnbind = false
                    onUnbind()
                }) { Text("فك الارتباط", color = Danger) }
            },
            dismissButton = {
                TextButton(onClick = { confirmUnbind = false }) { Text("إلغاء", color = Gold) }
            },
        )
    }
}
