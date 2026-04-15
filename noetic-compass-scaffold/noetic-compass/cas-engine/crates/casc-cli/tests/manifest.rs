use std::path::PathBuf;
use std::process::Command;

#[test]
fn manifest_runs_full_demo() {
    let binary = env!("CARGO_BIN_EXE_casc");
    let manifest =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../docs/CAS_FULL_DEMO.caspkg.toml");
    let status = Command::new(binary)
        .args(["--manifest", manifest.to_str().unwrap(), "--mode", "check"])
        .status()
        .expect("casc binary runs");
    assert!(status.success());
}

#[test]
fn manifest_directory_runs_full_demo() {
    let binary = env!("CARGO_BIN_EXE_casc");
    let manifest_dir =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../examples/full-demo");
    let status = Command::new(binary)
        .args([
            "--manifest",
            manifest_dir.to_str().unwrap(),
            "--mode",
            "check",
        ])
        .status()
        .expect("casc binary runs on directory manifest");
    assert!(status.success());
}

#[test]
fn logo_flag_prints_cas_banner() {
    let binary = env!("CARGO_BIN_EXE_casc");
    let output = Command::new(binary)
        .arg("--logo")
        .output()
        .expect("casc logo runs");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("C A S"));
    assert!(stdout.contains("Cognitive"));
}
