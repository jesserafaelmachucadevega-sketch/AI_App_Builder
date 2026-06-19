# AI-app-builder

AI multi-agent app builder for Android — Builder, Analyst, Designer agents; local GGUF/Ollama and hosted providers.

## Overview

- Orchestrates a three-agent pipeline (Builder → Analyst → Designer) with streaming, approvals, and workspace snapshots.
- Supports local GGUF imports (Gemma, etc.), on-device inference (llama.cpp JNI/NDK), and remote providers (OpenRouter, OpenAI, Hugging Face, Stability).
- Includes model license metadata handling (MODEL_LICENSES), import consent UI, and snapshot/export tooling.

## Quick start

1. Clone the repo.
2. Add API keys and hosts in Settings (or use .env / Android Keystore).
3. Download desired GGUF model(s) locally or add them to your Ollama host; do NOT commit model weights to the repo.
4. Open in Android Studio -> Build and run the `app` module (scaffold will be added in subsequent commits).

## Model licenses & imports

- Model metadata lives in `MODEL_LICENSES/manifest.json`. We do NOT include weights in this repo — users must download and import models themselves.
- The app will require users to accept each model’s license before enabling it.

## Contributing

- Please do not submit PRs that add model weight files or large binaries (>10MB).
- See `CONTRIBUTING.md` for guidelines (added in later commits).

## License

Project code licensed under Apache-2.0. See LICENSE.
