# Settings & Provider Setup

This document explains how the Settings screen populates provider defaults and how you can add API keys.

- Providers are defined in `config/providers.json` (read at runtime from assets by ProviderRegistry).
- Selecting a provider autofills the API URL, model dropdown, and shows a "Get API key" link.
- API keys are stored encrypted using AndroidX Security or Android Keystore — see Settings implementation.
- Use the "Test connection" button to validate keys and endpoints before saving.

If you want to add a new provider, edit `config/providers.json` and include the fields described in docs/provider-manifest.md.
