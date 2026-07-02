package com.example.pcremote

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import com.example.pcremote.network.WebSocketManager

class ConnectionService : Service() {

    private val binder = LocalBinder()
    private val webSocketManager = WebSocketManager()

    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onError: ((String) -> Unit)? = null

    var isConnected: Boolean = false
        private set
    private var currentHost: String = ""
    private var currentPort: Int = 8765

    inner class LocalBinder : Binder() {
        fun getService(): ConnectionService = this@ConnectionService
    }

    override fun onBind(intent: Intent?): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        webSocketManager.onConnected = {
            isConnected = true
            showNotification()
            onConnected?.invoke()
        }
        webSocketManager.onDisconnected = {
            isConnected = false
            hideNotification()
            onDisconnected?.invoke()
        }
        webSocketManager.onError = { msg ->
            isConnected = false
            hideNotification()
            onError?.invoke(msg)
        }
    }

    fun connect(host: String, port: Int) {
        currentHost = host
        currentPort = port
        webSocketManager.connect(host, port)
    }

    fun disconnect() {
        webSocketManager.disconnect()
        isConnected = false
        hideNotification()
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    fun send(message: Any) {
        if (isConnected) {
            webSocketManager.send(message)
        }
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "PC Remote Connection",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Shows when connected to PC"
            setShowBadge(false)
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    private fun showNotification() {
        val disconnectIntent = Intent(this, ConnectionService::class.java)
        disconnectIntent.action = ACTION_DISCONNECT
        val disconnectPendingIntent = PendingIntent.getService(
            this, 0, disconnectIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val openIntent = Intent(this, MainActivity::class.java)
        val openPendingIntent = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("PC Remote")
            .setContentText("Connected to $currentHost")
            .setSmallIcon(android.R.drawable.ic_menu_manage)
            .setOngoing(true)
            .setContentIntent(openPendingIntent)
            .addAction(
                android.R.drawable.ic_lock_power_off,
                "Spegni",
                disconnectPendingIntent
            )
            .build()

        startForeground(NOTIFICATION_ID, notification)
    }

    private fun hideNotification() {
        stopForeground(STOP_FOREGROUND_DETACH)
        val manager = getSystemService(NotificationManager::class.java)
        manager.cancel(NOTIFICATION_ID)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_DISCONNECT) {
            disconnect()
            stopSelf()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        disconnect()
        super.onDestroy()
    }

    companion object {
        const val CHANNEL_ID = "pc_remote_connection"
        const val NOTIFICATION_ID = 1001
        const val ACTION_DISCONNECT = "com.example.pcremote.DISCONNECT"
    }
}
