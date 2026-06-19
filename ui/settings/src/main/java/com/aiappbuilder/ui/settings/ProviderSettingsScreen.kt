package com.aiappbuilder.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.aiappbuilder.core.ProviderRegistry

/**
 * A Compose Settings screen stub that demonstrates provider selection and autofill behaviour.
 * This is a UI placeholder — wiring to real ViewModel/Repository will be added in follow-up commits.
 */
@Composable
fun ProviderSettingsScreen(context: android.content.Context) {
    LaunchedEffect(Unit) { ProviderRegistry.load(context) }
    var selectedProviderId by remember { mutableStateOf<String?>(null) }
    val providers = ProviderRegistry.all()

    Column {
        Text("Provider")
        // TODO: replace with a DropdownMenu composable that lists providers
        providers.forEach { p ->
            Button(onClick = { selectedProviderId = p.id }) { Text(p.displayName) }
        }

        val selected = selectedProviderId?.let { ProviderRegistry.findById(it) }
        OutlinedTextField(
            value = selected?.defaultApiUrl ?: "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            label = { Text("API URL") }
        )

        OutlinedTextField(
            value = selected?.keyFormatHint ?: "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Key hint") }
        )

        Button(onClick = { /* TODO: Test connection and save config */ }) { Text("Test & Save") }
    }
}
