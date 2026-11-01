package com.miftah.vpn.ui.screens

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Public
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.miftah.vpn.data.ProxyItem
import com.miftah.vpn.ui.theme.Emerald
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.SurfaceNavy
import com.miftah.vpn.ui.theme.SurfaceNavy2
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted

@Composable
fun ProxiesScreen(
    proxies: List<ProxyItem>,
    selectedProxyId: Int?,
    busy: Boolean,
    onSelect: (ProxyItem) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
    ) {
        Spacer(Modifier.height(14.dp))
        Text(
            text = "اختر البروكسي",
            color = TextMain,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            text = "القائمة يحددها المدير. لا يمكن إدخال عنوان يدوياً، ويُغيَّر فقط عنوان البروكسي في الإعداد المعتمد.",
            color = TextMuted,
            fontSize = 12.sp,
        )
        Spacer(Modifier.height(16.dp))

        if (proxies.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("لا توجد بروكسيات متاحة لحسابك", color = TextMuted, fontSize = 14.sp)
            }
            return@Column
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(proxies, key = { it.id }) { proxy ->
                val selected = proxy.id == selectedProxyId || proxy.selected
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(
                            width = if (selected) 1.5.dp else 1.dp,
                            color = if (selected) Gold else SurfaceNavy2,
                            shape = RoundedCornerShape(16.dp),
                        )
                        .clickable(enabled = !busy) { onSelect(proxy) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceNavy),
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier
                                .size(38.dp)
                                .background(SurfaceNavy2, CircleShape),
                            contentAlignment = Alignment.Center,
                        ) {
                            Icon(
                                Icons.Filled.Public,
                                contentDescription = null,
                                tint = if (selected) Gold else TextMuted,
                                modifier = Modifier.size(20.dp),
                            )
                        }
                        Spacer(Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = proxy.name,
                                color = TextMain,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Spacer(Modifier.height(2.dp))
                            Text(text = proxy.address, color = TextMuted, fontSize = 12.sp)
                        }
                        if (selected) {
                            Box(
                                modifier = Modifier
                                    .size(26.dp)
                                    .background(Emerald.copy(alpha = 0.18f), CircleShape),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    Icons.Filled.Check,
                                    contentDescription = "محدد",
                                    tint = Emerald,
                                    modifier = Modifier.size(16.dp),
                                )
                            }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(20.dp)) }
        }
    }
}
