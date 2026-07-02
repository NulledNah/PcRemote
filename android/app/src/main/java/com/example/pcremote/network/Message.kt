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
