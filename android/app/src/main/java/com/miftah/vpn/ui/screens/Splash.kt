package com.miftah.vpn.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted

@Composable
fun SplashScreen() {
    ScreenBackground {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            LogoMark(size = 104.dp)
            Spacer(Modifier.height(22.dp))
            Text(
                text = "MIFTAH",
                color = TextMain,
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 8.sp,
            )
            Spacer(Modifier.height(4.dp))
            Text(text = "مفتاح", color = Gold, fontSize = 20.sp)
            Spacer(Modifier.height(10.dp))
            Text(text = "مفتاحك إلى اتصال آمن", color = TextMuted, fontSize = 13.sp)
            Spacer(Modifier.height(34.dp))
            CircularProgressIndicator(
                modifier = Modifier.size(26.dp),
                color = Gold,
                strokeWidth = 2.dp,
            )
        }
    }
}
