package com.aiappbuilder.core

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.InputStreamReader

/**
 * ProviderRegistry reads config/providers.json from assets and exposes provider metadata.
 * This is a simple loader used by the Settings UI to populate dropdowns and autofill defaults.
 */
object ProviderRegistry {
    data class Provider(
        val id: String,
        val displayName: String,
        val authType: String,
        val docsUrl: String,
        val defaultApiUrl: String,
        val defaultModelList: List<String> = emptyList(),
        val keyFormatHint: String = "",
        val testPath: String = "",
        val requiresOrganization: Boolean = false
    )

    private var providers: List<Provider> = emptyList()

    fun load(context: Context) {
        try {
            context.assets.open("config/providers.json").use { input ->
                val type = object : TypeToken<List<Provider>>() {}.type
                providers = Gson().fromJson(InputStreamReader(input), type)
            }
        } catch (e: Exception) {
            providers = emptyList()
        }
    }

    fun all(): List<Provider> = providers

    fun findById(id: String): Provider? = providers.find { it.id == id }
}
