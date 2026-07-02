package com.example.pcremote.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class ExtraKey(
    val label: String,
    val keyCode: String,
    val width: Float = 1f,
    val isModifier: Boolean = false
)

private val DEFAULT_KEYS = listOf(
    ExtraKey("Esc", "KEY_ESC", 0.9f, false),
    ExtraKey("Ctrl", "KEY_LEFTCTRL", 1.0f, true),
    ExtraKey("Alt", "KEY_LEFTALT", 1.0f, true),
    ExtraKey("Super", "KEY_LEFTMETA", 1.2f, true),
    ExtraKey("Tab", "KEY_TAB", 1.0f, false),
    ExtraKey("Del", "KEY_DELETE", 1.0f, false),
    ExtraKey("↑", "KEY_UP", 0.8f, false),
    ExtraKey("↓", "KEY_DOWN", 0.8f, false),
    ExtraKey("←", "KEY_LEFT", 0.8f, false),
    ExtraKey("→", "KEY_RIGHT", 0.8f, false),
    ExtraKey("F1", "KEY_F1", 0.8f, false),
    ExtraKey("F2", "KEY_F2", 0.8f, false),
    ExtraKey("F3", "KEY_F3", 0.8f, false),
    ExtraKey("F4", "KEY_F4", 0.8f, false),
    ExtraKey("F5", "KEY_F5", 0.8f, false),
    ExtraKey("F6", "KEY_F6", 0.8f, false),
    ExtraKey("F7", "KEY_F7", 0.8f, false),
    ExtraKey("F8", "KEY_F8", 0.8f, false),
    ExtraKey("F9", "KEY_F9", 0.8f, false),
    ExtraKey("F10", "KEY_F10", 0.9f, false),
    ExtraKey("F11", "KEY_F11", 0.9f, false),
    ExtraKey("F12", "KEY_F12", 0.9f, false),
)

@Composable
fun ExtraKeysBar(
    onKeyDown: (String) -> Unit,
    onKeyUp: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val modifierKeys = remember { mutableStateMapOf<String, Boolean>() }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 6.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        for (key in DEFAULT_KEYS) {
            val isActive = modifierKeys[key.keyCode] == true
            val bgColor = if (key.isModifier && isActive)
                MaterialTheme.colorScheme.primary
            else if (key.isModifier)
                MaterialTheme.colorScheme.surfaceContainerHighest
            else
                MaterialTheme.colorScheme.surfaceContainerHighest

            val textColor = if (key.isModifier && isActive)
                MaterialTheme.colorScheme.onPrimary
            else
                MaterialTheme.colorScheme.onSurface

            Box(
                modifier = Modifier
                    .width((48.dp * key.width).coerceAtLeast(40.dp))
                    .height(36.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(bgColor)
                    .clickable {
                        if (key.isModifier) {
                            val current = modifierKeys[key.keyCode] ?: false
                            if (current) {
                                modifierKeys[key.keyCode] = false
                                onKeyUp(key.keyCode)
                            } else {
                                modifierKeys[key.keyCode] = true
                                onKeyDown(key.keyCode)
                            }
                        } else {
                            onKeyDown(key.keyCode)
                            onKeyUp(key.keyCode)
                        }
                    },
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = key.label,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = textColor,
                    maxLines = 1
                )
            }
        }
    }
}
