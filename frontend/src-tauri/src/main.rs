#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::Path;
use std::process::Command;

fn compose(dir: &str, args: &[&str]) -> Result<String, String> {
    if !Path::new(dir).join("docker-compose.yml").exists() {
        return Err(format!("No docker-compose.yml found in {dir} — set the project directory in Settings"));
    }
    let out = Command::new("docker")
        .arg("compose")
        .args(args)
        .current_dir(dir)
        .output()
        .map_err(|e| format!("failed to run docker: {e}"))?;
    if out.status.success() {
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&out.stderr).to_string())
    }
}

#[tauri::command]
fn docker_available() -> bool {
    Command::new("docker")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[tauri::command]
fn stack_status(dir: String) -> Result<String, String> {
    compose(&dir, &["ps", "--all", "--format", "json"])
}

#[tauri::command]
fn start_stack(dir: String) -> Result<String, String> {
    compose(&dir, &["up", "-d", "--remove-orphans"])
}

#[tauri::command]
fn stop_stack(dir: String) -> Result<String, String> {
    compose(&dir, &["down"])
}

#[tauri::command]
fn service_logs(dir: String, service: String) -> Result<String, String> {
    compose(&dir, &["logs", "--no-color", "--tail", "200", &service])
}

#[tauri::command]
fn read_env(dir: String) -> Result<String, String> {
    let env = Path::new(&dir).join(".env");
    let example = Path::new(&dir).join(".env.example");
    fs::read_to_string(&env)
        .or_else(|_| fs::read_to_string(&example))
        .map_err(|e| format!("cannot read .env or .env.example in {dir}: {e}"))
}

#[tauri::command]
fn save_env(dir: String, content: String) -> Result<(), String> {
    fs::write(Path::new(&dir).join(".env"), content).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            docker_available,
            stack_status,
            start_stack,
            stop_stack,
            service_logs,
            read_env,
            save_env
        ])
        .run(tauri::generate_context!())
        .expect("error while running DevFoundry");
}
