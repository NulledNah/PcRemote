package com.example.pcremote

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
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
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning

class MainActivity : ComponentActivity() {

    private var viewModelRef: RemoteViewModel? = null

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { _ -> }

    private val scannerOptions = GmsBarcodeScannerOptions.Builder()
        .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
        .build()

    private fun scanQr() {
        val scanner = GmsBarcodeScanning.getClient(this, scannerOptions)
        scanner.startScan()
            .addOnSuccessListener { barcode ->
                barcode.rawValue?.let { url ->
                    val trimmed = url.trim()
                    if (trimmed.startsWith("ws://")) {
                        val withoutProtocol = trimmed.removePrefix("ws://")
                        val parts = withoutProtocol.split(":")
                        if (parts.size == 2) {
                            viewModelRef?.host = parts[0]
                            viewModelRef?.port = parts[1]
                            viewModelRef?.connect()
                        }
                    }
                }
            }
            .addOnFailureListener { _ -> }
            .addOnCanceledListener { }
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
                        Lifecycle.Event.ON_DESTROY -> viewModel.unbindService(this@MainActivity)
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
                    onScanQr = { scanQr() }
                )
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val vm = viewModelRef
        if (vm?.isConnected == true) {
            when (keyCode) {
                KeyEvent.KEYCODE_VOLUME_UP -> {
                    vm.sendPcVolume(vm.pcVolume + 5)
                    return true
                }
                KeyEvent.KEYCODE_VOLUME_DOWN -> {
                    vm.sendPcVolume(vm.pcVolume - 5)
                    return true
                }
            }
        }
        return super.onKeyDown(keyCode, event)
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
                isDarkMode = viewModel.isDarkMode,
                onToggleDarkMode = { viewModel.toggleDarkMode(it) },
                favorites = viewModel.favorites,
                onConnectToFavorite = { viewModel.connectToFavorite(it) },
                onRemoveFavorite = { viewModel.removeFavorite(it) },
                onRenameFavorite = { id, name -> viewModel.renameFavorite(id, name) },
                onSaveFavorite = { viewModel.addCurrentAsFavorite(it) }
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
