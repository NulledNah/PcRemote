package com.example.pcremote.network

data class MouseMove(
    val type: String = "mouse_move",
    val dx: Float,
    val dy: Float
)

data class MouseButton(
    val type: String,
    val button: String
)

data class MouseScroll(
    val type: String = "mouse_scroll",
    val dy: Float = 0f,
    val dx: Float = 0f
)

data class KeyAction(
    val type: String,
    val code: String
)

data class TextMessage(
    val type: String = "text",
    val text: String
)

data class VolGet(val type: String = "vol_get")

data class VolSet(
    val type: String = "vol_set",
    val volume: Int
)

data class VolMute(val type: String = "vol_mute")

data class VolState(
    val type: String = "vol_state",
    val volume: Int = 50,
    val muted: Boolean = false
)
