package com.miftah.vpn.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Navy = Color(0xFF0B1220)
val SurfaceNavy = Color(0xFF131D2E)
val SurfaceNavy2 = Color(0xFF1B2940)
val Gold = Color(0xFFD4AF37)
val GoldSoft = Color(0xFFE8C766)
val Emerald = Color(0xFF2ECC71)
val Danger = Color(0xFFE74C3C)
val TextMain = Color(0xFFE9EEF7)
val TextMuted = Color(0xFF8FA0B8)

private val DarkColors = darkColorScheme(
    primary = Gold,
    onPrimary = Navy,
    secondary = Emerald,
    onSecondary = Navy,
    background = Navy,
    onBackground = TextMain,
    surface = SurfaceNavy,
    onSurface = TextMain,
    surfaceVariant = SurfaceNavy2,
    onSurfaceVariant = TextMuted,
    error = Danger,
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF8A6D1F),
    secondary = Color(0xFF1E8E4E),
)

@Composable
fun MiftahTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else DarkColors,
        content = content,
    )
}
