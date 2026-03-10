import os

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
except ImportError:
    os.system("pip install cryptography")
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

# Generate a new private key
private_key = ed25519.Ed25519PrivateKey.generate()

# Extract public key as hex for our Rust backend
public_key = private_key.public_key()
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
public_hex = public_bytes.hex()

print(f"Update PUBLIC_KEY_HEX in Rust to: {public_hex}")

# The message we are signing
base_key = "YTS-TEST-PRO-2026"
hwid = "WIN-MOCK-HWID-001"
message = f"{base_key}|{hwid}".encode('utf-8')

# Sign the message
signature = private_key.sign(message)
signature_hex = signature.hex()

print(f"\nYour valid license key is:")
print(f"{base_key}.{signature_hex}")
