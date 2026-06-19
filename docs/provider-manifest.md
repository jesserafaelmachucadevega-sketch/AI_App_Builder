# Provider manifest schema (config/providers.json)

Each provider entry should include the following fields:

- id: short identifier used in code (e.g. "openrouter")
- displayName: human-friendly name
- authType: "api_key" | "oauth" | "none"
- docsUrl: URL to provider signup/docs
- defaultApiUrl: default base URL to autofill
- defaultModelList: an array of common model ids
- keyFormatHint: short text shown to the user describing the key format
- testPath: a relative path used by the Test Connection flow
- requiresOrganization: true/false

Example is provided in repo: config/providers.json
