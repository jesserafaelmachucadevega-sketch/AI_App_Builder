# Model License & Import Guidelines

1. Downloading Models
   - Download models from the model provider's official page (Hugging Face, Ollama library, Stability, etc.).
   - Verify checksums (SHA256) for files you download.

2. Importing into the App
   - Open Settings → Models → Import Model.
   - The app displays model metadata and the license URL/summary.
   - You must check "I accept and will comply with this model's license" before the model is enabled.

3. Packaging / Distribution
   - Do NOT put model weights in the Git repository.
   - If you plan to ship an APK that includes model weights, ensure the model license permits redistribution and include required notices.

4. Compliance
   - The app will store the user's acceptance record (model id, checksum, timestamp) in its database for auditing.

If you need per-model license text mirrored in the repo, request "Include full model LICENSE texts" and I'll add them where redistribution is permitted.
