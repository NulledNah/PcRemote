package com.example.pcremote.viewmodel

import android.app.Application
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.content.SharedPreferences
import android.os.IBinder
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.pcremote.ConnectionService
import com.example.pcremote.network.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

class RemoteViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs: SharedPreferences =
        application.getSharedPreferences("pc_remote_prefs", Context.MODE_PRIVATE)

    private var service: ConnectionService? = null
    private var bound = false

    var host by mutableStateOf("")
    var port by mutableStateOf("8765")
    var isConnected by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var useAutocorrect by mutableStateOf(true)
    var scrollSensitivity by mutableStateOf(1f)
    var scrollInverted by mutableStateOf(false)
    var moveSensitivity by mutableStateOf(0.7f)
    var savedHost by mutableStateOf("")
    var savedPort by mutableStateOf("")
    var isDarkMode by mutableStateOf(false)
    var pcVolume by mutableIntStateOf(50)
    var pcMuted by mutableStateOf(false)
    private var lastVolCmdTime = 0L
    private var preMuteVolume = 0

    init {
        savedHost = prefs.getString("saved_host", "") ?: ""
        savedPort = prefs.getString("saved_port", "") ?: ""
        isDarkMode = prefs.getBoolean("dark_mode", false)
    }

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            service = (binder as ConnectionService.LocalBinder).getService()
            bound = true

            service?.onConnected = {
                isConnected = true
                error = null
                prefs.edit()
                    .putString("saved_host", host)
                    .putString("saved_port", port)
                    .apply()
                savedHost = host
                savedPort = port
                fetchVolume()
                startVolumePolling()
            }
            service?.onDisconnected = {
                isConnected = false
            }
            service?.onError = { msg ->
                error = msg
                isConnected = false
            }
            service?.setOnMessageListener { text ->
                handleServerMessage(text)
            }

            isConnected = service?.isConnected ?: false
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            service = null
            bound = false
            isConnected = false
        }
    }

    fun bindService(context: Context) {
        if (!bound) {
            val intent = Intent(context, ConnectionService::class.java)
            context.bindService(intent, connection, Context.BIND_AUTO_CREATE)
            context.startService(intent)
        }
    }

    fun unbindService(context: Context) {
        if (bound) {
            context.unbindService(connection)
            bound = false
        }
    }

    fun toggleDarkMode(enabled: Boolean) {
        isDarkMode = enabled
        prefs.edit().putBoolean("dark_mode", enabled).apply()
    }

    fun connect() {
        if (!isConnected) {
            val portNum = port.toIntOrNull() ?: 8765
            error = null
            service?.connect(host, portNum)
        }
    }

    fun fetchVolume() {
        service?.send(VolGet())
    }

    fun sendPcVolume(vol: Int) {
        val clamped = vol.coerceIn(0, 100)
        if (!pcMuted) {
            preMuteVolume = clamped
        }
        lastVolCmdTime = System.currentTimeMillis()
        service?.send(VolSet(volume = clamped))
    }

    fun togglePcMute() {
        val wasMuted = pcMuted
        pcMuted = !wasMuted
        lastVolCmdTime = System.currentTimeMillis()
        service?.send(VolMute())
        if (wasMuted) {
            sendPcVolume(preMuteVolume.coerceAtLeast(1))
        } else {
            preMuteVolume = pcVolume
        }
    }

    private fun startVolumePolling() {
        viewModelScope.launch {
            while (isConnected) {
                delay(1000)
                if (isConnected) fetchVolume()
            }
        }
    }

    private fun handleServerMessage(text: String) {
        try {
            val json = JSONObject(text)
            if (json.optString("type") == "vol_state") {
                pcVolume = json.optInt("volume", pcVolume)
                val from = json.optString("from")
                if (from == "vol_mute" || from == "vol_set" ||
                    System.currentTimeMillis() - lastVolCmdTime > 500
                ) {
                    pcMuted = json.optBoolean("muted", pcMuted)
                }
            }
        } catch (e: Exception) {
            Log.e("PcRemote", "Failed to parse server msg: $text", e)
        }
    }

    fun disconnect() {
        service?.disconnect()
        isConnected = false
    }

    fun sendMouseMove(dx: Float, dy: Float) {
        service?.send(MouseMove("mouse_move", dx, dy))
    }

    fun sendMouseDown(button: String) {
        service?.send(MouseButton("mouse_down", button))
    }

    fun sendMouseUp(button: String) {
        service?.send(MouseButton("mouse_up", button))
    }

    fun sendMouseClick(button: String = "left") {
        sendMouseDown(button)
        viewModelScope.launch {
            delay(30)
            sendMouseUp(button)
        }
    }

    fun sendMiddleClick() {
        sendMouseClick("middle")
    }

    fun sendMouseScroll(dy: Float = 0f, dx: Float = 0f) {
        service?.send(MouseScroll("mouse_scroll", dy, dx))
    }

    fun sendKeyDown(code: String) {
        service?.send(KeyAction("key_down", code))
    }

    fun sendKeyUp(code: String) {
        service?.send(KeyAction("key_up", code))
    }

    fun sendKeyTap(code: String) {
        sendKeyDown(code)
        sendKeyUp(code)
    }

    fun sendKeyEvent(keyCode: Int, isDown: Boolean) {
        val name = androidKeyToName(keyCode)
        if (name != null) {
            if (isDown) sendKeyDown(name) else sendKeyUp(name)
        }
    }

    fun sendComboKeyTap(charSequence: CharSequence) {
        service?.send(TextMessage("text", charSequence.toString()))
    }

    fun sendText(text: String) {
        service?.send(TextMessage("text", text))
    }

    fun sendChar(c: Char) {
        val entry = charToKeyName(c)
        if (entry != null) {
            if (entry.needsShift) sendKeyDown("KEY_LEFTSHIFT")
            sendKeyDown(entry.baseKey)
            sendKeyUp(entry.baseKey)
            if (entry.needsShift) sendKeyUp("KEY_LEFTSHIFT")
        }
    }

    override fun onCleared() {
        super.onCleared()
    }

    companion object {
        data class KeyEntry(val baseKey: String, val needsShift: Boolean)

        val ANDROID_KEY_MAP = mapOf(
            android.view.KeyEvent.KEYCODE_A to "KEY_A",
            android.view.KeyEvent.KEYCODE_B to "KEY_B",
            android.view.KeyEvent.KEYCODE_C to "KEY_C",
            android.view.KeyEvent.KEYCODE_D to "KEY_D",
            android.view.KeyEvent.KEYCODE_E to "KEY_E",
            android.view.KeyEvent.KEYCODE_F to "KEY_F",
            android.view.KeyEvent.KEYCODE_G to "KEY_G",
            android.view.KeyEvent.KEYCODE_H to "KEY_H",
            android.view.KeyEvent.KEYCODE_I to "KEY_I",
            android.view.KeyEvent.KEYCODE_J to "KEY_J",
            android.view.KeyEvent.KEYCODE_K to "KEY_K",
            android.view.KeyEvent.KEYCODE_L to "KEY_L",
            android.view.KeyEvent.KEYCODE_M to "KEY_M",
            android.view.KeyEvent.KEYCODE_N to "KEY_N",
            android.view.KeyEvent.KEYCODE_O to "KEY_O",
            android.view.KeyEvent.KEYCODE_P to "KEY_P",
            android.view.KeyEvent.KEYCODE_Q to "KEY_Q",
            android.view.KeyEvent.KEYCODE_R to "KEY_R",
            android.view.KeyEvent.KEYCODE_S to "KEY_S",
            android.view.KeyEvent.KEYCODE_T to "KEY_T",
            android.view.KeyEvent.KEYCODE_U to "KEY_U",
            android.view.KeyEvent.KEYCODE_V to "KEY_V",
            android.view.KeyEvent.KEYCODE_W to "KEY_W",
            android.view.KeyEvent.KEYCODE_X to "KEY_X",
            android.view.KeyEvent.KEYCODE_Y to "KEY_Y",
            android.view.KeyEvent.KEYCODE_Z to "KEY_Z",
            android.view.KeyEvent.KEYCODE_0 to "KEY_0",
            android.view.KeyEvent.KEYCODE_1 to "KEY_1",
            android.view.KeyEvent.KEYCODE_2 to "KEY_2",
            android.view.KeyEvent.KEYCODE_3 to "KEY_3",
            android.view.KeyEvent.KEYCODE_4 to "KEY_4",
            android.view.KeyEvent.KEYCODE_5 to "KEY_5",
            android.view.KeyEvent.KEYCODE_6 to "KEY_6",
            android.view.KeyEvent.KEYCODE_7 to "KEY_7",
            android.view.KeyEvent.KEYCODE_8 to "KEY_8",
            android.view.KeyEvent.KEYCODE_9 to "KEY_9",
            android.view.KeyEvent.KEYCODE_SPACE to "KEY_SPACE",
            android.view.KeyEvent.KEYCODE_ENTER to "KEY_ENTER",
            android.view.KeyEvent.KEYCODE_DEL to "KEY_BACKSPACE",
            android.view.KeyEvent.KEYCODE_FORWARD_DEL to "KEY_DELETE",
            android.view.KeyEvent.KEYCODE_TAB to "KEY_TAB",
            android.view.KeyEvent.KEYCODE_ESCAPE to "KEY_ESC",
            android.view.KeyEvent.KEYCODE_MINUS to "KEY_MINUS",
            android.view.KeyEvent.KEYCODE_EQUALS to "KEY_EQUAL",
            android.view.KeyEvent.KEYCODE_LEFT_BRACKET to "KEY_LEFTBRACE",
            android.view.KeyEvent.KEYCODE_RIGHT_BRACKET to "KEY_RIGHTBRACE",
            android.view.KeyEvent.KEYCODE_BACKSLASH to "KEY_BACKSLASH",
            android.view.KeyEvent.KEYCODE_SEMICOLON to "KEY_SEMICOLON",
            android.view.KeyEvent.KEYCODE_APOSTROPHE to "KEY_APOSTROPHE",
            android.view.KeyEvent.KEYCODE_COMMA to "KEY_COMMA",
            android.view.KeyEvent.KEYCODE_PERIOD to "KEY_DOT",
            android.view.KeyEvent.KEYCODE_SLASH to "KEY_SLASH",
            android.view.KeyEvent.KEYCODE_GRAVE to "KEY_GRAVE",
            android.view.KeyEvent.KEYCODE_SHIFT_LEFT to "KEY_LEFTSHIFT",
            android.view.KeyEvent.KEYCODE_SHIFT_RIGHT to "KEY_RIGHTSHIFT",
            android.view.KeyEvent.KEYCODE_CTRL_LEFT to "KEY_LEFTCTRL",
            android.view.KeyEvent.KEYCODE_CTRL_RIGHT to "KEY_RIGHTCTRL",
            android.view.KeyEvent.KEYCODE_ALT_LEFT to "KEY_LEFTALT",
            android.view.KeyEvent.KEYCODE_ALT_RIGHT to "KEY_RIGHTALT",
            android.view.KeyEvent.KEYCODE_META_LEFT to "KEY_LEFTMETA",
            android.view.KeyEvent.KEYCODE_META_RIGHT to "KEY_RIGHTMETA",
            android.view.KeyEvent.KEYCODE_DPAD_UP to "KEY_UP",
            android.view.KeyEvent.KEYCODE_DPAD_DOWN to "KEY_DOWN",
            android.view.KeyEvent.KEYCODE_DPAD_LEFT to "KEY_LEFT",
            android.view.KeyEvent.KEYCODE_DPAD_RIGHT to "KEY_RIGHT",
            android.view.KeyEvent.KEYCODE_MOVE_HOME to "KEY_HOME",
            android.view.KeyEvent.KEYCODE_MOVE_END to "KEY_END",
            android.view.KeyEvent.KEYCODE_PAGE_UP to "KEY_PAGEUP",
            android.view.KeyEvent.KEYCODE_PAGE_DOWN to "KEY_PAGEDOWN",
            android.view.KeyEvent.KEYCODE_INSERT to "KEY_INSERT",
            android.view.KeyEvent.KEYCODE_CAPS_LOCK to "KEY_CAPSLOCK",
            android.view.KeyEvent.KEYCODE_NUM_LOCK to "KEY_NUMLOCK",
            android.view.KeyEvent.KEYCODE_SCROLL_LOCK to "KEY_SCROLLLOCK",
            android.view.KeyEvent.KEYCODE_F1 to "KEY_F1",
            android.view.KeyEvent.KEYCODE_F2 to "KEY_F2",
            android.view.KeyEvent.KEYCODE_F3 to "KEY_F3",
            android.view.KeyEvent.KEYCODE_F4 to "KEY_F4",
            android.view.KeyEvent.KEYCODE_F5 to "KEY_F5",
            android.view.KeyEvent.KEYCODE_F6 to "KEY_F6",
            android.view.KeyEvent.KEYCODE_F7 to "KEY_F7",
            android.view.KeyEvent.KEYCODE_F8 to "KEY_F8",
            android.view.KeyEvent.KEYCODE_F9 to "KEY_F9",
            android.view.KeyEvent.KEYCODE_F10 to "KEY_F10",
            android.view.KeyEvent.KEYCODE_F11 to "KEY_F11",
            android.view.KeyEvent.KEYCODE_F12 to "KEY_F12",
        )

        fun androidKeyToName(keyCode: Int): String? = ANDROID_KEY_MAP[keyCode]

        fun charToKeyName(c: Char): KeyEntry? {
            return when {
                c in 'a'..'z' -> KeyEntry("KEY_${c.uppercaseChar()}", false)
                c in 'A'..'Z' -> KeyEntry("KEY_$c", true)
                c in '0'..'9' -> KeyEntry("KEY_$c", false)
                c == ' ' -> KeyEntry("KEY_SPACE", false)
                c == '\n' -> KeyEntry("KEY_ENTER", false)
                c == '\t' -> KeyEntry("KEY_TAB", false)
                c == '-' -> KeyEntry("KEY_MINUS", false)
                c == '=' -> KeyEntry("KEY_EQUAL", false)
                c == '[' -> KeyEntry("KEY_LEFTBRACE", false)
                c == ']' -> KeyEntry("KEY_RIGHTBRACE", false)
                c == '\\' -> KeyEntry("KEY_BACKSLASH", false)
                c == ';' -> KeyEntry("KEY_SEMICOLON", false)
                c == '\'' -> KeyEntry("KEY_APOSTROPHE", false)
                c == ',' -> KeyEntry("KEY_COMMA", false)
                c == '.' -> KeyEntry("KEY_DOT", false)
                c == '/' -> KeyEntry("KEY_SLASH", false)
                c == '`' -> KeyEntry("KEY_GRAVE", false)
                c == '!' -> KeyEntry("KEY_1", true)
                c == '@' -> KeyEntry("KEY_2", true)
                c == '#' -> KeyEntry("KEY_3", true)
                c == '$' -> KeyEntry("KEY_4", true)
                c == '%' -> KeyEntry("KEY_5", true)
                c == '^' -> KeyEntry("KEY_6", true)
                c == '&' -> KeyEntry("KEY_7", true)
                c == '*' -> KeyEntry("KEY_8", true)
                c == '(' -> KeyEntry("KEY_9", true)
                c == ')' -> KeyEntry("KEY_0", true)
                c == '_' -> KeyEntry("KEY_MINUS", true)
                c == '+' -> KeyEntry("KEY_EQUAL", true)
                c == '{' -> KeyEntry("KEY_LEFTBRACE", true)
                c == '}' -> KeyEntry("KEY_RIGHTBRACE", true)
                c == '|' -> KeyEntry("KEY_BACKSLASH", true)
                c == ':' -> KeyEntry("KEY_SEMICOLON", true)
                c == '"' -> KeyEntry("KEY_APOSTROPHE", true)
                c == '<' -> KeyEntry("KEY_COMMA", true)
                c == '>' -> KeyEntry("KEY_DOT", true)
                c == '?' -> KeyEntry("KEY_SLASH", true)
                c == '~' -> KeyEntry("KEY_GRAVE", true)
                else -> null
            }
        }
    }
}
