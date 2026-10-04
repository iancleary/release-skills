# Copy this recipe into the consumer justfile. Keep positional forwarding.
[positional-arguments]
release *args:
    uv run scripts/release.py "$@"
