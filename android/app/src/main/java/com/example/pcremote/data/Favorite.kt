package com.example.pcremote.data

import java.util.UUID

data class Favorite(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val host: String,
    val port: Int,
    val lastUsed: Long = System.currentTimeMillis()
)
