package com.example.pcremote

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.pcremote.ui.ConnectionScreen
import com.example.pcremote.ui.PCRemoteTheme
import com.example.pcremote.ui.RemoteScreen
import com.example.pcremote.viewmodel.RemoteViewModel
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

class MainActivity : ComponentActivity() {

    private var viewModelRef: RemoteViewModel? = null

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { _ -> }

    private val qrScanLauncher = registerForActivityResult(ScanContract()) { result ->
        result?.contents?.let { url ->
            val wsUrl = url.trim()
            if (wsUrl.startsWith("ws://")) {
                val withoutProtocol = wsUrl.removePrefix("ws://")
                val parts = withoutProtocol.split(":")
                if (parts.size == 2) {
                    viewModelRef?.host = parts[0]
                    viewModelRef?.port = parts[1]
                    viewModelRef?.connect()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this, Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        setContent {
            val viewModel: RemoteViewModel = viewModel()
            viewModelRef = viewModel

            val lifecycleOwner = LocalLifecycleOwner.current

            DisposableEffect(lifecycleOwner) {
                val observer = LifecycleEventObserver { _, event ->
                    when (event) {
                        Lifecycle.Event.ON_START -> viewModel.bindService(this@MainActivity)
                        Lifecycle.Event.ON_STOP -> viewModel.unbindService(this@MainActivity)
                        else -> {}
                    }
                }
                lifecycleOwner.lifecycle.addObserver(observer)
                onDispose {
                    lifecycleOwner.lifecycle.removeObserver(observer)
                }
            }

            PCRemoteTheme(darkTheme = viewModel.isDarkMode) {
                PCRemoteApp(
                    viewModel = viewModel,
                    onScanQr = {
                        val options = ScanOptions().apply {
                            setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                            setPrompt("Scan QR code from server terminal")
                            setBeepEnabled(false)
                            setOrientationLocked(true)
                        }
                        qrScanLauncher.launch(options)
                    }
                )
            }
        }
    }
}

enum class Screen {
    CONNECTION, REMOTE
}

@Composable
fun PCRemoteApp(
    viewModel: RemoteViewModel,
    onScanQr: () -> Unit
) {
    var currentScreen by remember { mutableStateOf(Screen.CONNECTION) }

    LaunchedEffect(viewModel.isConnected) {
        if (!viewModel.isConnected && currentScreen == Screen.REMOTE) {
            currentScreen = Screen.CONNECTION
        }
    }

    when (currentScreen) {
        Screen.CONNECTION -> {
            ConnectionScreen(
                host = viewModel.host,
                port = viewModel.port,
                isConnected = viewModel.isConnected,
                error = viewModel.error,
                onHostChange = { viewModel.host = it },
                onPortChange = { viewModel.port = it },
                onConnect = { viewModel.connect() },
                onDisconnect = { viewModel.disconnect() },
                onContinue = { currentScreen = Screen.REMOTE },
                onScanQr = onScanQr,
                savedHost = viewModel.savedHost,
                savedPort = viewModel.savedPort,
                onUseSaved = {
                    viewModel.host = viewModel.savedHost
                    viewModel.port = viewModel.savedPort
                }
            )
        }
        Screen.REMOTE -> {
            RemoteScreen(
                viewModel = viewModel,
                onDisconnect = {
                    viewModel.disconnect()
                    currentScreen = Screen.CONNECTION
                }
            )
        }
    }
}
