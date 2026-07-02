package com.example.pcremote.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.abs

private const val TAP_DISTANCE_THRESHOLD = 25f
private const val DOUBLE_TAP_WINDOW_MS = 400L

@Composable
fun TrackpadArea(
    onMouseMove: (Float, Float) -> Unit,
    onLeftClick: () -> Unit,
    onRightClick: () -> Unit,
    onScroll: (Float, Float) -> Unit,
    onMouseDown: () -> Unit,
    onMouseUp: () -> Unit,
    onMiddleClick: () -> Unit,
    moveSensitivity: Float = 0.7f,
    scrollSensitivity: Float = 1f,
    scrollInverted: Boolean = false,
    modifier: Modifier = Modifier,
) {
    var totalDist by remember { mutableFloatStateOf(0f) }
    var dragActive by remember { mutableStateOf(false) }
    var twoFingerActive by remember { mutableStateOf(false) }
    var secondStartX by remember { mutableFloatStateOf(0f) }
    var secondStartY by remember { mutableFloatStateOf(0f) }
    var pointerCount by remember { mutableFloatStateOf(0f) }
    var lastTapTime by remember { mutableLongStateOf(0L) }
    var tapCount by remember { mutableFloatStateOf(0f) }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .pointerInput(moveSensitivity, scrollSensitivity) {
                awaitPointerEventScope {
                    while (true) {
                        val event = awaitPointerEvent()
                        val active = event.changes.filter { it.pressed }
                        val now = event.changes.firstOrNull()?.uptimeMillis ?: 0L

                        when {
                            active.isEmpty() -> {
                                if (dragActive) {
                                    onMouseUp()
                                    tapCount = 0f
                                } else if (totalDist < TAP_DISTANCE_THRESHOLD) {
                                    when {
                                        pointerCount == 3f -> onMiddleClick()
                                        pointerCount == 2f -> onRightClick()
                                        pointerCount == 1f -> {
                                            if (tapCount == 1f &&
                                                now - lastTapTime < DOUBLE_TAP_WINDOW_MS &&
                                                now - lastTapTime > 0L
                                            ) {
                                                // Second tap completed fast
                                                tapCount = 2f
                                            } else {
                                                onLeftClick()
                                                lastTapTime = now
                                                tapCount = 1f
                                            }
                                        }
                                    }
                                }
                                if (tapCount >= 2f &&
                                    now - lastTapTime > DOUBLE_TAP_WINDOW_MS
                                ) {
                                    tapCount = 0f
                                }
                                totalDist = 0f
                                dragActive = false
                                twoFingerActive = false
                                pointerCount = 0f
                            }
                            active.size == 1 && !twoFingerActive -> {
                                pointerCount = 1f
                                val ptr = active[0]
                                if (!ptr.previousPressed) {
                                    totalDist = 0f

                                    if (tapCount >= 1f &&
                                        now - lastTapTime > DOUBLE_TAP_WINDOW_MS
                                    ) {
                                        tapCount = 0f
                                    }
                                    if (tapCount >= 1f &&
                                        now - lastTapTime < DOUBLE_TAP_WINDOW_MS &&
                                        now - lastTapTime > 0L
                                    ) {
                                        tapCount = 2f
                                        dragActive = true
                                        onMouseDown()
                                    }
                                } else {
                                    val dx = ptr.position.x - ptr.previousPosition.x
                                    val dy = ptr.position.y - ptr.previousPosition.y
                                    val step = abs(dx) + abs(dy)
                                    totalDist += step

                                    if (dragActive) {
                                        if (step > 0.3f) {
                                            onMouseMove(
                                                accelerate(dx, moveSensitivity),
                                                accelerate(dy, moveSensitivity),
                                            )
                                        }
                                    } else if (step > 0.3f) {
                                        onMouseMove(
                                            accelerate(dx, moveSensitivity),
                                            accelerate(dy, moveSensitivity),
                                        )
                                    }
                                }
                                ptr.consume()
                            }
                            active.size >= 2 -> {
                                if (dragActive) {
                                    onMouseUp()
                                    dragActive = false
                                }
                                twoFingerActive = true
                                pointerCount = active.size.toFloat()
                                tapCount = 0f

                                val lastPtr = active.last()
                                if (!lastPtr.previousPressed) {
                                    secondStartX = lastPtr.position.x
                                    secondStartY = lastPtr.position.y
                                } else {
                                    val dx = lastPtr.position.x - secondStartX
                                    val dy = lastPtr.position.y - secondStartY
                                    secondStartX = lastPtr.position.x
                                    secondStartY = lastPtr.position.y

                                    if (abs(dx) > 1f || abs(dy) > 1f) {
                                        totalDist += abs(dx) + abs(dy)
                                        val dir = if (scrollInverted) 1f else -1f
                                        onScroll(
                                            dx * scrollSensitivity * dir,
                                            dy * scrollSensitivity * dir,
                                        )
                                    }
                                }
                                active.forEach { it.consume() }
                            }
                        }
                    }
                }
            }
            .padding(16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = "Swipe to move cursor · Tap to click\n2 fingers = scroll · 3 fingers = middle click",
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
            fontSize = 14.sp,
        )
    }
}

private fun accelerate(delta: Float, sensitivity: Float): Float {
    val sign = if (delta >= 0) 1f else -1f
    val absD = abs(delta)
    val accel = absD * (1f + absD * 0.04f)
    return sign * accel * sensitivity
}
