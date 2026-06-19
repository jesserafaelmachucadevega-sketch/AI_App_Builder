package com.aiappbuilder.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "provider_configs")
data class ProviderConfig(
    @PrimaryKey val providerId: String,
    val apiUrl: String,
    val encryptedKeyAlias: String?,
    val authType: String,
    val validatedAt: Long? = null
)

@Entity(tableName = "agent_defaults")
data class AgentDefault(
    @PrimaryKey val agentType: String, // e.g. builder, analyst, designer
    val providerId: String,
    val modelId: String
)

@Entity(tableName = "model_manifest")
data class ModelManifest(
    @PrimaryKey val modelId: String,
    val displayName: String?,
    val source: String?,
    val licenseUrl: String?,
    val checksumSha256: String?
)
