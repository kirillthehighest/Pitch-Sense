//! The desktop window of PitchSense (Phase 22). It starts the Python server (`python -m app.api`
//! while developing, the packaged `pitchsense-server` in a package), reads the port the server
//! announces on its first line (`PITCHSENSE_PORT=<port>`), gives the interface the server's
//! address through the `backend_url` command, and stops the server when the window closes. The
//! server also watches its input, so it ends even when this process is killed. When the server
//! stops before it listens (no database, say), `backend_url` answers with what it wrote on its
//! error output, which the interface shows.

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager, RunEvent, State};

#[derive(Default)]
struct Server {
    url: Mutex<Option<String>>,
    problem: Mutex<Option<String>>,
    child: Mutex<Option<Child>>,
}

/// The server's address once it listens; `None` while it starts; an error when it stopped
/// without listening.
#[tauri::command]
fn backend_url(server: State<Server>) -> Result<Option<String>, String> {
    if let Some(url) = server.url.lock().unwrap().clone() {
        return Ok(Some(url));
    }
    match server.problem.lock().unwrap().clone() {
        Some(problem) => Err(problem),
        None => Ok(None),
    }
}

/// The packaged server, or the project's Python while developing.
fn server_command(app: &AppHandle) -> Command {
    let name = if cfg!(windows) {
        "pitchsense-server.exe"
    } else {
        "pitchsense-server"
    };
    let packaged = app
        .path()
        .resolve(format!("server/{name}"), BaseDirectory::Resource);
    if let Ok(packaged) = packaged
        && packaged.is_file()
    {
        let mut command = Command::new(packaged);
        command.arg("--with-window");
        return command;
    }
    // web/src-tauri -> the project's root, whose .venv holds the Python of the project
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..");
    let python = if cfg!(windows) {
        root.join(".venv").join("Scripts").join("python.exe")
    } else {
        root.join(".venv").join("bin").join("python")
    };
    let mut command = Command::new(python);
    command
        .args(["-m", "app.api", "--with-window"])
        .current_dir(root);
    if let Ok(extra) = std::env::var("PITCHSENSE_SERVER_ARGS") {
        command.args(extra.split_whitespace()); // developers' options, such as --preferences
    }
    command
}

fn start_server(app: &AppHandle) -> std::io::Result<()> {
    let mut command = server_command(app);
    // The server ends when its input closes: when this process ends in any way, even killed
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW: no console beside the window
    }
    let mut child = command.spawn()?;
    let stdout = child.stdout.take().expect("the server's output is piped");
    let stderr = child
        .stderr
        .take()
        .expect("the server's error output is piped");
    // What the server reports (passed on to this program's error output as well)
    let errors = std::thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stderr).lines().map_while(Result::ok) {
            eprintln!("{line}");
            lines.push(line);
        }
        lines
    });
    let handle = app.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(port) = line.trim().strip_prefix("PITCHSENSE_PORT=") {
                let url = format!("http://127.0.0.1:{port}");
                *handle.state::<Server>().url.lock().unwrap() = Some(url);
            }
        }
        // The output ended: the server stopped. Before it listened, say why.
        let server = handle.state::<Server>();
        if server.url.lock().unwrap().is_none() {
            let reported = errors.join().unwrap_or_default();
            let last = reported.iter().rev().find(|line| !line.trim().is_empty());
            let problem = last.map_or("Serverul local s-a oprit la pornire.", |line| line.as_str());
            *server.problem.lock().unwrap() = Some(problem.to_string());
        }
    });
    *app.state::<Server>().child.lock().unwrap() = Some(child);
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Server::default())
        .setup(|app| {
            start_server(app.handle())?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_url])
        .build(tauri::generate_context!())
        .expect("the window could not be built")
        .run(|app, event| {
            if let RunEvent::Exit = event
                && let Some(mut child) = app.state::<Server>().child.lock().unwrap().take()
            {
                let _ = child.kill(); // its worker process ends with it
                let _ = child.wait();
            }
        });
}
