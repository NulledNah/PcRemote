package com.example.pcremote.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightScheme = lightColorScheme(
    primary = Color(0xFF6B493A),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFDF0D9),
    onPrimaryContainer = Color(0xFF3B2A22),
    secondary = Color(0xFF7F5A49),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFEBE0D3),
    onSecondaryContainer = Color(0xFF3B2A22),
    tertiary = Color(0xFF5C7A5F),
    onTertiary = Color.White,
    tertiaryContainer = Color(0xFFDFF0E0),
    onTertiaryContainer = Color(0xFF1A2F1C),
    error = Color(0xFFBA1A1A),
    onError = Color.White,
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF410002),
    background = Color(0xFFFDF0D9),
    onBackground = Color(0xFF3B2A22),
    surface = Color(0xFFFDF0D9),
    onSurface = Color(0xFF3B2A22),
    surfaceVariant = Color(0xFFEBE0D3),
    onSurfaceVariant = Color(0xFF5C4033),
    surfaceContainerHighest = Color(0xFFE5D9CA),
    surfaceContainerHigh = Color(0xFFEDE2D4),
    outline = Color(0xFF8B7355),
    outlineVariant = Color(0xFFC4B5A5),
    inverseSurface = Color(0xFF3B2A22),
    inverseOnSurface = Color(0xFFFDF0D9),
    inversePrimary = Color(0xFFD4A88C),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFFD4A88C),
    onPrimary = Color(0xFF3B2A22),
    primaryContainer = Color(0xFF5C4033),
    onPrimaryContainer = Color(0xFFFDF0D9),
    secondary = Color(0xFFC9B7A7),
    onSecondary = Color(0xFF3B2A22),
    secondaryContainer = Color(0xFF5C4033),
    onSecondaryContainer = Color(0xFFEBE0D3),
    tertiary = Color(0xFFA8C9A9),
    onTertiary = Color(0xFF1A2F1C),
    tertiaryContainer = Color(0xFF3D5A3F),
    onTertiaryContainer = Color(0xFFDFF0E0),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    background = Color(0xFF1A1210),
    onBackground = Color(0xFFEBE0D3),
    surface = Color(0xFF1A1210),
    onSurface = Color(0xFFEBE0D3),
    surfaceVariant = Color(0xFF5C4033),
    onSurfaceVariant = Color(0xFFD4C4B5),
    surfaceContainerHighest = Color(0xFF2B1F1A),
    surfaceContainerHigh = Color(0xFF241914),
    outline = Color(0xFF9E8E7F),
    outlineVariant = Color(0xFF5C4033),
    inverseSurface = Color(0xFFEBE0D3),
    inverseOnSurface = Color(0xFF3B2A22),
    inversePrimary = Color(0xFF6B493A),
)

@Composable
fun PCRemoteTheme(
    darkTheme: Boolean,
    content: @Composable () -> Unit
) {
    val scheme = if (darkTheme) DarkScheme else LightScheme
    MaterialTheme(colorScheme = scheme, content = content)
}
