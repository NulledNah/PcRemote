package com.example.pcremote.network

import com.google.gson.Gson
import okhttp3.*
import java.util.concurrent.TimeUnit

class WebSocketManager {

    private val client: OkHttpClient = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val gson = Gson()

    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onError: ((String) -> Unit)? = null
    var onMessage: ((String) -> Unit)? = null

    val isConnected: Boolean
        get() = webSocket != null

    fun connect(host: String, port: Int) {
        val url = "ws://$host:$port"
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onConnected?.invoke()
            }

            override fun onFailure(
                webSocket: WebSocket,
                t: Throwable,
                response: Response?
            ) {
                webSocket.close(1000, null)
                this@WebSocketManager.webSocket = null
                onDisconnected?.invoke()
                onError?.invoke(t.message ?: "Connection lost")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                this@WebSocketManager.webSocket = null
                onDisconnected?.invoke()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                onMessage?.invoke(text)
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
    }

    fun send(message: Any) {
        val json = gson.toJson(message)
        webSocket?.send(json)
    }
}
