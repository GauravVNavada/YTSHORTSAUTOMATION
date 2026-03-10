use ring::signature;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct LicenseResponse {
    valid: bool,
    message: String,
}

// Our public key for verifying license signatures
// Handled as hex string for easy portability
const PUBLIC_KEY_HEX: &str = "97cb3e05e34a1bb072027b65f43e74a02f2a6b8ca67d42e8e69565f34fc2a2f2";

// In a real app we'd use machine-uid crate. Mocking for this build.
fn get_hwid() -> String {
    "WIN-MOCK-HWID-001".to_string()
}

#[tauri::command]
fn validate_license(key: String) -> LicenseResponse {
    // Format expected: YTS-XXXX-XXXX-XXXX.SIGNATURE_HEX
    let parts: Vec<&str> = key.split('.').collect();
    if parts.len() != 2 {
        return LicenseResponse {
            valid: false,
            message: "Invalid license format. Expected KEY.SIGNATURE".into(),
        };
    }

    let base_key = parts[0];
    let signature_hex = parts[1];

    // Read public key
    let pk_bytes = match hex::decode(PUBLIC_KEY_HEX) {
        Ok(b) => b,
        Err(_) => return LicenseResponse { valid: false, message: "Internal PK error".into() }
    };

    // Decode signature
    let sig_bytes = match hex::decode(signature_hex) {
        Ok(b) => b,
        Err(_) => return LicenseResponse { valid: false, message: "Invalid signature encoding".into() }
    };

    // Message being signed is: base_key + hwid
    let hwid = get_hwid();
    let message = format!("{}|{}", base_key, hwid);

    // Verify
    let peer_public_key = signature::UnparsedPublicKey::new(&signature::ED25519, &pk_bytes);
    
    match peer_public_key.verify(message.as_bytes(), &sig_bytes) {
        Ok(_) => LicenseResponse {
            valid: true,
            message: "License verified and bound to this machine.".into()
        },
        Err(_) => LicenseResponse {
            valid: false,
            message: "Signature verification failed. Key may be for a different machine.".into()
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![validate_license])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
