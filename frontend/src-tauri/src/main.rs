#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::HashMap;
use std::fs;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{Emitter, Manager};

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

fn autostart_log(msg: &str) {
    use std::io::Write;
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open("/tmp/devfoundry-autostart.log") {
        let _ = writeln!(f, "{msg}");
    }
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

    let log_path = Path::new(dir).join("orchestrator.log");
    let log_file = fs::File::create(&log_path).map_err(|e| format!("cannot create {log_path:?}: {e}"))?;
    let log_err = log_file.try_clone().map_err(|e| e.to_string())?;

    autostart_log(&format!("spawning: {program:?} {args:?} (cwd {backend_dir:?})"));
    Command::new(&program)
        .args(&args)
        .current_dir(&backend_dir)
        .envs(&env_vars)
        .stdout(Stdio::from(log_file))
        .stderr(Stdio::from(log_err))
        .spawn()
        .map_err(|e| {
            autostart_log(&format!("spawn failed: {e}"));
            format!("failed to start orchestrator: {e}")
        })
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
fn system_specs() -> HashMap<String, String> {
    let mut s = HashMap::new();
    s.insert("arch".into(), std::env::consts::ARCH.to_string());
    s.insert("os".into(), std::env::consts::OS.to_string());

    #[cfg(target_os = "macos")]
    {
        let sysctl = |k: &str| Command::new("sysctl").args(["-n", k]).output().ok()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
        let mem_bytes: u64 = sysctl("hw.memsize").parse().unwrap_or(0);
        s.insert("ram_gb".into(), (mem_bytes / 1_073_741_824).to_string());
        s.insert("cpu_cores".into(), sysctl("hw.ncpu"));
        let chip = sysctl("machdep.cpu.brand_string");
        s.insert("chip".into(), if chip.is_empty() { "Apple Silicon".into() } else { chip });
        // Apple Silicon has an integrated Metal GPU sharing unified memory.
        s.insert("gpu".into(), if std::env::consts::ARCH == "aarch64" { "Apple Metal (unified)".into() } else { "".into() });
    }
    #[cfg(not(target_os = "macos"))]
    {
        s.insert("ram_gb".into(), "0".into());
        s.insert("cpu_cores".into(), "0".into());
        s.insert("chip".into(), "unknown".into());
        s.insert("gpu".into(), "".into());
    }
    s
}

#[tauri::command]
fn open_url_window(app: tauri::AppHandle, url: String, label: String, title: String) -> Result<(), String> {
    // Open an external URL in a native child webview — bypasses X-Frame-Options
    // (used for the FreeLLMAPI dashboard and deployed-app previews).
    if let Some(w) = app.get_webview_window(&label) {
        let _ = w.set_focus();
        return Ok(());
    }
    let parsed = url.parse().map_err(|e| format!("bad url: {e}"))?;
    tauri::WebviewWindowBuilder::new(&app, &label, tauri::WebviewUrl::External(parsed))
        .title(title)
        .inner_size(1200.0, 820.0)
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
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

// ---- Live dev server for Canvas preview -----------------------------------
struct DevServers(Mutex<HashMap<String, Child>>);

fn free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .ok()
        .and_then(|l| l.local_addr().ok())
        .map(|a| a.port())
        .unwrap_or(5199)
}

#[tauri::command]
fn start_dev_server(project_dir: String, state: tauri::State<DevServers>) -> Result<u16, String> {
    let dir = Path::new(&project_dir);
    if !dir.join("package.json").exists() {
        return Err("no package.json — this project has no dev server".into());
    }
    let mut servers = state.0.lock().unwrap();
    if servers.contains_key(&project_dir) {
        return Err("dev server already running for this project".into());
    }
    let port = free_port();
    // Vite/Next honor --port; pass through both common conventions.
    let child = Command::new("npm")
        .args(["run", "dev", "--", "--port", &port.to_string(), "--host", "127.0.0.1"])
        .current_dir(dir)
        .env("PORT", port.to_string())
        .env("BROWSER", "none")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("failed to start dev server: {e}"))?;
    servers.insert(project_dir, child);
    Ok(port)
}

#[tauri::command]
fn stop_dev_server(project_dir: String, state: tauri::State<DevServers>) -> Result<(), String> {
    if let Some(mut child) = state.0.lock().unwrap().remove(&project_dir) {
        let _ = child.kill();
    }
    Ok(())
}

// ---- Keychain-backed secrets (macOS `security`) ---------------------------
const KEYCHAIN_SERVICE: &str = "com.devfoundry.app";

#[tauri::command]
fn keychain_set(key: String, value: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let out = Command::new("security")
            .args(["add-generic-password", "-U", "-a", &key, "-s", KEYCHAIN_SERVICE, "-w", &value])
            .output()
            .map_err(|e| e.to_string())?;
        if out.status.success() { Ok(()) } else { Err(String::from_utf8_lossy(&out.stderr).into()) }
    }
    #[cfg(not(target_os = "macos"))]
    { Err("keychain only implemented on macOS".into()) }
}

#[tauri::command]
fn keychain_get(key: String) -> Result<String, String> {
    #[cfg(target_os = "macos")]
    {
        let out = Command::new("security")
            .args(["find-generic-password", "-a", &key, "-s", KEYCHAIN_SERVICE, "-w"])
            .output()
            .map_err(|e| e.to_string())?;
        if out.status.success() {
            Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
        } else {
            Ok(String::new()) // not found → empty
        }
    }
    #[cfg(not(target_os = "macos"))]
    { Ok(String::new()) }
}

#[tauri::command]
fn keychain_delete(key: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("security")
            .args(["delete-generic-password", "-a", &key, "-s", KEYCHAIN_SERVICE])
            .output();
        Ok(())
    }
    #[cfg(not(target_os = "macos"))]
    { Ok(()) }
}

fn show_main(app: &tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

fn main() {
    use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
    use tauri::tray::{TrayIconBuilder, TrayIconEvent};
    use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState};

    // Global hotkey: ⌘⇧A (Ctrl⇧A on Win/Linux) → show & focus the app.
    let toggle_shortcut = Shortcut::new(Some(Modifiers::SUPER | Modifiers::SHIFT), Code::KeyA);

    tauri::Builder::default()
        .manage(BackendProc(Mutex::new(None)))
        .manage(DevServers(Mutex::new(HashMap::new())))
        .plugin(tauri_plugin_notification::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, sc, event| {
                    if event.state == ShortcutState::Pressed && sc == &toggle_shortcut {
                        show_main(app);
                        let _ = app.emit("global-forge", ());
                    }
                })
                .build(),
        )
        .setup(move |app| {
            // Auto-start the embedded orchestrator so the app is self-contained.
            let state = app.state::<BackendProc>();
            if backend_port_open() {
                autostart_log("autostart: port 9100 already in use — skipping spawn");
            } else {
                match spawn_backend(DEFAULT_PROJECT_DIR) {
                    Ok(child) => {
                        autostart_log(&format!("autostart: orchestrator pid {}", child.id()));
                        *state.0.lock().unwrap() = Some(child);
                    }
                    Err(e) => autostart_log(&format!("autostart failed: {e}")),
                }
            }

            // Register the global shortcut.
            use tauri_plugin_global_shortcut::GlobalShortcutExt;
            let _ = app.global_shortcut().register(toggle_shortcut);

            // ---- Native application menu ----
            let handle = app.handle();
            let forge = MenuItem::with_id(handle, "nav:forge", "New Forge", true, Some("CmdOrCtrl+N"))?;
            let research = MenuItem::with_id(handle, "nav:research", "Deep Research", true, Some("CmdOrCtrl+R"))?;
            let history = MenuItem::with_id(handle, "nav:runs", "History", true, Some("CmdOrCtrl+Y"))?;
            let models = MenuItem::with_id(handle, "nav:models", "Models", true, Some("CmdOrCtrl+M"))?;
            let settings = MenuItem::with_id(handle, "nav:settings", "Settings", true, Some("CmdOrCtrl+,"))?;
            let palette = MenuItem::with_id(handle, "cmd:palette", "Command Palette", true, Some("CmdOrCtrl+K"))?;
            let docs = MenuItem::with_id(handle, "help:docs", "Documentation", true, None::<&str>)?;

            let app_menu = Submenu::with_items(handle, "DevFoundry", true, &[
                &PredefinedMenuItem::about(handle, Some("About DevFoundry"), None)?,
                &PredefinedMenuItem::separator(handle)?,
                &settings,
                &PredefinedMenuItem::separator(handle)?,
                &PredefinedMenuItem::hide(handle, None)?,
                &PredefinedMenuItem::quit(handle, None)?,
            ])?;
            let file_menu = Submenu::with_items(handle, "File", true, &[
                &forge, &research, &PredefinedMenuItem::separator(handle)?, &history,
            ])?;
            let edit_menu = Submenu::with_items(handle, "Edit", true, &[
                &PredefinedMenuItem::undo(handle, None)?,
                &PredefinedMenuItem::redo(handle, None)?,
                &PredefinedMenuItem::separator(handle)?,
                &PredefinedMenuItem::cut(handle, None)?,
                &PredefinedMenuItem::copy(handle, None)?,
                &PredefinedMenuItem::paste(handle, None)?,
                &PredefinedMenuItem::select_all(handle, None)?,
            ])?;
            let go_menu = Submenu::with_items(handle, "Go", true, &[
                &forge, &research, &history, &models, &PredefinedMenuItem::separator(handle)?, &palette,
            ])?;
            let window_menu = Submenu::with_items(handle, "Window", true, &[
                &PredefinedMenuItem::minimize(handle, None)?,
                &PredefinedMenuItem::maximize(handle, None)?,
                &PredefinedMenuItem::fullscreen(handle, None)?,
            ])?;
            let help_menu = Submenu::with_items(handle, "Help", true, &[&docs])?;
            let menu = Menu::with_items(handle, &[&app_menu, &file_menu, &edit_menu, &go_menu, &window_menu, &help_menu])?;
            app.set_menu(menu)?;
            app.on_menu_event(|app, event| {
                let id = event.id().0.as_str();
                if let Some(page) = id.strip_prefix("nav:") {
                    show_main(app);
                    let _ = app.emit("navigate", page.to_string());
                } else if id == "cmd:palette" {
                    show_main(app);
                    let _ = app.emit("open-palette", ());
                } else if id == "help:docs" {
                    let _ = app.emit("open-docs", ());
                }
            });

            // ---- System tray ----
            let tray_forge = MenuItem::with_id(handle, "tray:forge", "New Forge", true, None::<&str>)?;
            let tray_show = MenuItem::with_id(handle, "tray:show", "Show DevFoundry", true, None::<&str>)?;
            let tray_quit = MenuItem::with_id(handle, "tray:quit", "Quit", true, None::<&str>)?;
            let tray_menu = Menu::with_items(handle, &[&tray_show, &tray_forge, &PredefinedMenuItem::separator(handle)?, &tray_quit])?;
            let _tray = TrayIconBuilder::with_id("main-tray")
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("DevFoundry")
                .menu(&tray_menu)
                .on_menu_event(|app, event| match event.id().0.as_str() {
                    "tray:show" => show_main(app),
                    "tray:forge" => { show_main(app); let _ = app.emit("navigate", "forge".to_string()); }
                    "tray:quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { .. } = event {
                        show_main(tray.app_handle());
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let bstate = window.state::<BackendProc>();
                if let Some(mut child) = bstate.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
                let dstate = window.state::<DevServers>();
                for (_, mut child) in dstate.0.lock().unwrap().drain() {
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            docker_available,
            docker_running,
            open_url_window,
            system_specs,
            start_docker_desktop,
            stack_status,
            start_stack,
            stop_stack,
            service_logs,
            read_env,
            save_env,
            start_dev_server,
            stop_dev_server,
            keychain_set,
            keychain_get,
            keychain_delete
        ])
        .run(tauri::generate_context!())
        .expect("error while running DevFoundry");
}
