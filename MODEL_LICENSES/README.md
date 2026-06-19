This folder contains metadata and license links for third-party models referenced by this project.

Important:
- Model binaries (GGUF, weights, etc.) are NOT included in this repository.
- Users must download models themselves and confirm they comply with the model license before importing.
- The app's import UI will show the license_url and require the user to accept the license before the model is enabled.

How to add a model entry:
- After downloading a model, compute SHA256 and add a manifest entry with checksum_sha256.
- If license text can be redistributed, include MODEL_LICENSES/<model-id>/LICENSE.txt; otherwise include a link in license_url.
