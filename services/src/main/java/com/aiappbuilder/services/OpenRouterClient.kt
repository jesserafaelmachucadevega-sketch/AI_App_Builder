package com.aiappbuilder.services

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class OpenRouterClient(private val baseUrl: String, private val apiKey: String) {
    suspend fun testConnection(): Result<String> = withContext(Dispatchers.IO) {
        try {
            // TODO: perform a real HTTP request using apiKey
            Result.success("ok")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
