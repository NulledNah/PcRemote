package com.example.pcremote.data

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class FavoriteRepository(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("pc_remote_favorites", Context.MODE_PRIVATE)
    private val gson = Gson()
    private val appContext = context.applicationContext

    fun loadFavorites(): List<Favorite> {
        val migrated = migrateLegacy()
        if (migrated != null) return migrated

        val json = prefs.getString(KEY_FAVORITES, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<Favorite>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun saveFavorites(favorites: List<Favorite>) {
        val json = gson.toJson(favorites)
        prefs.edit().putString(KEY_FAVORITES, json).apply()
    }

    fun addFavorite(name: String, host: String, port: Int): List<Favorite> {
        val favorites = loadFavorites().toMutableList()
        if (favorites.any { it.host == host && it.port == port }) return favorites

        val entry = Favorite(
            name = name,
            host = host,
            port = port,
            lastUsed = System.currentTimeMillis()
        )
        favorites.add(0, entry)
        saveFavorites(favorites)
        return favorites
    }

    fun removeFavorite(id: String): List<Favorite> {
        val favorites = loadFavorites().filter { it.id != id }
        saveFavorites(favorites)
        return favorites
    }

    fun renameFavorite(id: String, newName: String): List<Favorite> {
        val favorites = loadFavorites().map {
            if (it.id == id) it.copy(name = newName) else it
        }
        saveFavorites(favorites)
        return favorites
    }

    fun bumpFavorite(id: String): List<Favorite> {
        val favorites = loadFavorites().map {
            if (it.id == id) it.copy(lastUsed = System.currentTimeMillis()) else it
        }.sortedByDescending { it.lastUsed }
        saveFavorites(favorites)
        return favorites
    }

    private fun migrateLegacy(): List<Favorite>? {
        val legacyPrefs = appContext.getSharedPreferences("pc_remote_prefs", Context.MODE_PRIVATE)
        val savedHost = legacyPrefs.getString("saved_host", "") ?: ""
        val savedPort = legacyPrefs.getString("saved_port", "") ?: ""

        if (savedHost.isBlank() || savedPort.isBlank()) return null
        if (prefs.contains(KEY_FAVORITES)) return null

        val port = savedPort.toIntOrNull() ?: return null
        val favorites = listOf(
            Favorite(name = "Recent", host = savedHost, port = port)
        )
        saveFavorites(favorites)
        legacyPrefs.edit().remove("saved_host").remove("saved_port").apply()
        return favorites
    }

    companion object {
        private const val KEY_FAVORITES = "favorites"
    }
}
