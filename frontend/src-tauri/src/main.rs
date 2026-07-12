#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::HashMap;
use std::fs;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

const DEFAULT_PROJECT_DIR: &str = "/Users/jahblesslion/Documents/devfoundry";

struct BackendProc(Mutex<Option<Child>>);

fn backend_port_open() -> bool {
    TcpStream::connect(("127.0.0.1", 9100)).is_ok()
}

fn parse_env_file(dir: &str) -> HashMap<String, String> {
    let mut vars = HashMap::new();
    for candidate in [".env", ".env.example"] {
        if let Ok(text) = fs::read_to_string(Path::new(dir).join(candidate)) {
            for line in text.lines() {
                if let Some((k, v)) = line.split_once('=') {
                    let k = k.trim();
                    if !k.is_empty() && !k.starts_with('#') {
                        vars.entry(k.to_string()).or_insert_with(|| v.trim().to_string());
                    }
                }
            }
            break;
        }
    }
    vars
}

fn find_uvicorn(backend_dir: &Path) -> Option<(PathBuf, Vec<String>)> {
    let venv = backend_dir.join(".venv/bin/uvicorn");
    if venv.exists() {
        return Some((venv, vec![]));
    }
    for py in ["python3", "python"] {
        if Command::new(py).arg("--version").output().map(|o| o.status.success()).unwrap_or(false) {
            return Some((PathBuf::from(py), vec!["-m".into(), "uvicorn".into()]));
        }
    }
    None
}

fn spawn_backend(dir: &str) -> Result<Child, String> {
    let backend_dir = Path::new(dir).join("backend");
    if !backend_dir.join("app/main.py").exists() {
        return Err(format!("backend not found under {dir} — set the project directory in Settings"));
    }
    let (program, mut args) = find_uvicorn(&backend_dir)
        .ok_or("Python not found. Install Python 3.11+ or create backend/.venv")?;
    args.extend(["app.main:app".into(), "--host".into(), "127.0.0.1".into(), "--port".into(), "9100".into()]);

    let mut env_vars = parse_env_file(dir);
    env_vars.entry("DEVFOUNDRY_EMBEDDED".into()).or_insert_with(|| "1".into());
    env_vars.insert(
        "DEVFOUNDRY_WORKSPACE".into(),
        Path::new(dir).join("workspace").to_string_lossy().into_owned(),
    );

    Command::new(program)
        .args(&args)
        .current_dir(&backend_dir)
        .envs(&env_vars)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("failed to start orchestrator: {e}"))
}

#[tauri::command]
fn start_backend(dir: String, state: tauri::State<BackendProc>) -> Result<String, String> {
    if backend_port_open() {
        return Ok("already running".into());
    }
    let child = spawn_backend(&dir)?;
    *state.0.lock().unwrap() = Some(child);
    Ok("started".into())
}

#[tauri::command]
fn stop_backend(state: tauri::State<BackendProc>) -> Result<(), String> {
    if let Some(mut child) = state.0.lock().unwrap().take() {
        child.kill().map_err(|e| e.to_string())?;
    }
    Ok(())
}

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
    Command::new("docker").arg("--version").output().map(|o| o.status.success()).unwrap_or(false)
}

#[tauri::command]
fn docker_running() -> bool {
    Command::new("docker").arg("info").output().map(|o| o.status.success()).unwrap_or(false)
}

#[tauri::command]
fn start_docker_desktop() -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .args(["-a", "Docker"])
            .output()
            .map_err(|e| format!("could not launch Docker Desktop: {e}"))
            .and_then(|o| {
                if o.status.success() {
                    Ok(())
                } else {
                    Err(String::from_utf8_lossy(&o.stderr).to_string())
                }
            })
    }
    #[cfg(not(target_os = "macos"))]
    {
        Err("automatic Docker startup is only implemented on macOS".into())
    }
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
        .manage(BackendProc(Mutex::new(None)))
        .setup(|app| {
            // Auto-start the embedded orchestrator so the app is self-contained.
            let state = app.state::<BackendProc>();
            if !backend_port_open() {
                match spawn_backend(DEFAULT_PROJECT_DIR) {
                    Ok(child) => *state.0.lock().unwrap() = Some(child),
                    Err(e) => eprintln!("embedded orchestrator autostart failed: {e}"),
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendProc>();
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            docker_available,
            docker_running,
            start_docker_desktop,
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
