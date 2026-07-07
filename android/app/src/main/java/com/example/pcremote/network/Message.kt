package com.example.pcremote.network

import com.google.gson.annotations.SerializedName

data class MouseMove(
    @SerializedName("t") val type: String = "m",
    @SerializedName("x") val dx: Float,
    @SerializedName("y") val dy: Float
)

data class MouseButton(
    @SerializedName("t") val type: String,
    @SerializedName("b") val button: String
)

data class MouseScroll(
    @SerializedName("t") val type: String = "s",
    @SerializedName("y") val dy: Float = 0f,
    @SerializedName("x") val dx: Float = 0f
)

data class KeyAction(
    @SerializedName("t") val type: String,
    @SerializedName("c") val code: String
)

data class TextMessage(
    @SerializedName("t") val type: String = "tx",
    @SerializedName("tx") val text: String
)

data class VolGet(@SerializedName("t") val type: String = "vg")

data class VolSet(
    @SerializedName("t") val type: String = "vs",
    @SerializedName("v") val volume: Int
)

data class VolMute(@SerializedName("t") val type: String = "vm")
