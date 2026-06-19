package com.aiappbuilder.services

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * A minimal Ollama client stub.
 * Implement actual networking with Retrofit/OkHttp in follow-up.
 */
class OllamaClient(private val baseUrl: String) {
    suspend fun testConnection(): Result<String> = withContext(Dispatchers.IO) {
        try {
            // TODO: perform a real HTTP request
            Result.success("ok")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
