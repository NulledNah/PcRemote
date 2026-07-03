package com.example.pcremote.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pcremote.viewmodel.RemoteViewModel

@Composable
fun RemoteScreen(
    viewModel: RemoteViewModel,
    onDisconnect: () -> Unit
) {
    var showSettings by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.primary)
                .padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "PC Remote",
                color = MaterialTheme.colorScheme.onPrimary,
                fontSize = 18.sp
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { showSettings = !showSettings }) {
                    Text(
                        "\u2699",
                        color = MaterialTheme.colorScheme.onPrimary,
                        fontSize = 20.sp
                    )
                }
                TextButton(onClick = onDisconnect) {
                    Text(
                        "Disconnect",
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.surfaceContainerHigh)
                .padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(
                onClick = { viewModel.togglePcMute() },
                modifier = Modifier.size(32.dp)
            ) {
                Icon(
                    if (viewModel.pcMuted) Icons.Filled.VolumeOff else Icons.Filled.VolumeUp,
                    contentDescription = if (viewModel.pcMuted) "Unmute" else "Mute",
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(20.dp)
                )
            }
            Slider(
                value = viewModel.pcVolume.toFloat(),
                onValueChange = { viewModel.sendPcVolume(it.toInt()) },
                valueRange = 0f..100f,
                modifier = Modifier.weight(1f)
            )
            Text(
                "${viewModel.pcVolume}%",
                fontSize = 13.sp,
                modifier = Modifier.width(40.dp),
                color = MaterialTheme.colorScheme.onSurface
            )
        }

        if (showSettings) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Settings",
                        style = MaterialTheme.typography.titleSmall,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Dark mode")
                        Switch(
                            checked = viewModel.isDarkMode,
                            onCheckedChange = { viewModel.toggleDarkMode(it) }
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Autocorrect")
                        Switch(
                            checked = viewModel.useAutocorrect,
                            onCheckedChange = { viewModel.useAutocorrect = it }
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Invert scroll")
                        Switch(
                            checked = viewModel.scrollInverted,
                            onCheckedChange = { viewModel.scrollInverted = it }
                        )
                    }
                    Text("Scroll sensitivity: ${"%.1f".format(viewModel.scrollSensitivity)}")
                    Slider(
                        value = viewModel.scrollSensitivity,
                        onValueChange = { viewModel.scrollSensitivity = it },
                        valueRange = 0.2f..3f,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Text("Move sensitivity: ${"%.1f".format(viewModel.moveSensitivity)}")
                    Slider(
                        value = viewModel.moveSensitivity,
                        onValueChange = { viewModel.moveSensitivity = it },
                        valueRange = 0.2f..2f,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        TrackpadArea(
            onMouseMove = { dx, dy ->
                viewModel.sendMouseMove(dx, dy)
            },
            onLeftClick = {
                viewModel.sendMouseClick("left")
            },
            onRightClick = {
                viewModel.sendMouseClick("right")
            },
            onScroll = { dx, dy ->
                viewModel.sendMouseScroll(dy = dy, dx = dx)
            },
            onMouseDown = {
                viewModel.sendMouseDown("left")
            },
            onMouseUp = {
                viewModel.sendMouseUp("left")
            },
            onMiddleClick = {
                viewModel.sendMiddleClick()
            },
            moveSensitivity = viewModel.moveSensitivity,
            scrollSensitivity = viewModel.scrollSensitivity,
            scrollInverted = viewModel.scrollInverted,
            modifier = Modifier.weight(1f)
        )

        ExtraKeysBar(
            onKeyDown = { code -> viewModel.sendKeyDown(code) },
            onKeyUp = { code -> viewModel.sendKeyUp(code) }
        )

        KeyboardInputArea(
            onKeyEvent = { keyCode, isDown ->
                viewModel.sendKeyEvent(keyCode, isDown)
            },
            onComboText = { text ->
                viewModel.sendComboKeyTap(text)
            },
            onEnter = {
                viewModel.sendKeyTap("KEY_ENTER")
            },
            onBackspace = {
                viewModel.sendKeyTap("KEY_BACKSPACE")
            },
            useAutocorrect = viewModel.useAutocorrect
        )
    }
}
