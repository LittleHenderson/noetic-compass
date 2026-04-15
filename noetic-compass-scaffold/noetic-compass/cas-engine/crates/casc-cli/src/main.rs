use std::env;
use std::fs;
use std::io::{self, IsTerminal, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::thread;
use std::time::Duration;

use cas_engine::language::{compile_expression, compile_file};
use casc_syntax::{lex as frontend_lex, parse_source as frontend_parse, CAS_GRAMMAR_BNF};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct PackageSection {
    name: Option<String>,
    version: Option<String>,
    entry: String,
}

#[derive(Debug, Deserialize)]
struct CasManifest {
    package: PackageSection,
}

fn print_json(value: &serde_json::Value) {
    println!("{}", serde_json::to_string_pretty(value).unwrap());
}

const LOGO_FRAMES: [&str; 6] = [
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  o o  '.   \     Architecture
   |   /     ^     \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '.       .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _/ \_
         /_/ \_\"#,
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  O o  '.   \     Architecture
   |   /     ~     \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '.   *   .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _\ /_
         /_/ \_\"#,
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  O O  '.   \     Architecture
   |   /     -     \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '.  -*-  .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _/ \_
         \_\ /_/"#,
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  o O  '.   \     Architecture
   |   /     ^     \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '.   +   .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _\ /_
         \_\ /_/"#,
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  o o  '.   \     Architecture
   |   /     ^     \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '.  .*.  .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _/ \_
         /_/ \_\"#,
    r#"          .-""""-.
       .-'  .-.  '-.        C A S
     .'   .'   '.   '.      Cognitive
    /   .'  ^ ^  '.   \     Architecture
   |   /    \_/    \   |    System
   |   |   \___/   |   |    compiler :: parse :: type :: run
    \   '. \ | / .'   /
     '.   '-._.-'   .'
       '-._____.-.'
          _\ /_
         /_/ \_\"#,
];

fn print_logo(animated: bool) {
    if animated && io::stdout().is_terminal() {
        for _ in 0..2 {
            for frame in LOGO_FRAMES {
                print!("\x1B[2J\x1B[H{frame}\n");
                let _ = io::stdout().flush();
                thread::sleep(Duration::from_millis(85));
            }
        }
    }
    println!("{}", LOGO_FRAMES[0]);
}

fn run_frontend_mode(mode: &str, source: &str) -> i32 {
    match mode {
        "lex" => match frontend_lex(source) {
            Ok(tokens) => {
                print_json(&serde_json::json!({"tokens": tokens, "valid": true, "error": null}));
                0
            }
            Err(error) => {
                print_json(
                    &serde_json::json!({"tokens": [], "valid": false, "error": error.to_string()}),
                );
                1
            }
        },
        "parse" => match frontend_parse(source) {
            Ok(ast) => {
                print_json(&serde_json::json!({"ast": ast, "valid": true, "error": null}));
                0
            }
            Err(error) => {
                print_json(
                    &serde_json::json!({"ast": null, "valid": false, "error": error.to_string()}),
                );
                1
            }
        },
        _ => unreachable!(),
    }
}

fn run_mode(mode: &str, artifact: serde_json::Value) -> i32 {
    match mode {
        "lex" => print_json(&serde_json::json!({
            "tokens": artifact["tokens"],
            "valid": artifact["valid"],
            "error": artifact["error"],
        })),
        "parse" => print_json(&serde_json::json!({
            "ast": artifact["ast"],
            "valid": artifact["valid"],
            "error": artifact["error"],
        })),
        "check" => print_json(&serde_json::json!({
            "type": artifact["type"],
            "warnings": artifact["warnings"],
            "valid": artifact["valid"],
            "error": artifact["error"],
        })),
        _ => print_json(&artifact),
    }
    if artifact["valid"].as_bool().unwrap_or(false) {
        0
    } else {
        1
    }
}

fn repl() -> i32 {
    print_logo(false);
    println!("CAS REPL. Type :quit to exit, :grammar to print the grammar.");
    loop {
        print!("casc> ");
        io::stdout().flush().unwrap();
        let mut line = String::new();
        if io::stdin().read_line(&mut line).is_err() {
            return 1;
        }
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if matches!(line, ":quit" | ":q" | "quit" | "exit") {
            return 0;
        }
        if line == ":grammar" {
            println!("{CAS_GRAMMAR_BNF}");
            continue;
        }
        let artifact = compile_expression(line).to_json();
        print_json(&artifact);
    }
}

fn resolve_manifest_entry(path: &str) -> Result<PathBuf, String> {
    let raw_path = PathBuf::from(path);
    let manifest_path = if raw_path.is_dir() {
        let upper = raw_path.join("Cas.toml");
        if upper.exists() {
            upper
        } else {
            raw_path.join("caspkg.toml")
        }
    } else {
        raw_path
    };
    let raw = fs::read_to_string(&manifest_path).map_err(|error| {
        format!(
            "failed to read manifest {}: {error}",
            manifest_path.display()
        )
    })?;
    let manifest: CasManifest = toml::from_str(&raw).map_err(|error| {
        format!(
            "failed to parse manifest {}: {error}",
            manifest_path.display()
        )
    })?;
    let base = manifest_path
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    let entry = base.join(&manifest.package.entry);
    let _ = (&manifest.package.name, &manifest.package.version);
    Ok(entry)
}

fn main() -> ExitCode {
    let mut args = env::args().skip(1);
    let mut mode = String::from("run");
    let mut file_path: Option<String> = None;
    let mut manifest_path: Option<String> = None;
    let mut grammar = false;
    let mut logo = false;
    let mut repl_mode = false;
    let mut expression: Option<String> = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--mode" => mode = args.next().unwrap_or_else(|| "run".to_string()),
            "--file" => file_path = args.next(),
            "--manifest" => manifest_path = args.next(),
            "--grammar" => grammar = true,
            "--logo" => logo = true,
            "--repl" => repl_mode = true,
            _ => expression = Some(arg),
        }
    }

    if logo {
        print_logo(true);
        return ExitCode::SUCCESS;
    }
    if grammar {
        println!("{CAS_GRAMMAR_BNF}");
        return ExitCode::SUCCESS;
    }
    if repl_mode {
        return ExitCode::from(repl() as u8);
    }

    if let Some(manifest_path) = manifest_path {
        match resolve_manifest_entry(&manifest_path) {
            Ok(entry) => {
                let artifact = compile_file(entry).to_json();
                return ExitCode::from(run_mode(&mode, artifact) as u8);
            }
            Err(error) => {
                print_json(&serde_json::json!({
                    "valid": false,
                    "error": error,
                }));
                return ExitCode::from(1);
            }
        }
    }

    if let Some(file_path) = file_path {
        if matches!(mode.as_str(), "lex" | "parse") {
            match fs::read_to_string(&file_path) {
                Ok(source) => return ExitCode::from(run_frontend_mode(&mode, &source) as u8),
                Err(error) => {
                    print_json(
                        &serde_json::json!({"valid": false, "error": format!("failed to read {file_path}: {error}")}),
                    );
                    return ExitCode::from(1);
                }
            }
        }
        let artifact = compile_file(file_path).to_json();
        return ExitCode::from(run_mode(&mode, artifact) as u8);
    }
    if let Some(expression) = expression {
        if matches!(mode.as_str(), "lex" | "parse") {
            return ExitCode::from(run_frontend_mode(&mode, &expression) as u8);
        }
        let artifact = compile_expression(&expression).to_json();
        return ExitCode::from(run_mode(&mode, artifact) as u8);
    }

    eprintln!("usage: casc '<expression>' | casc --file path | casc --manifest caspkg.toml [--mode lex|parse|check|run] [--grammar] [--logo] [--repl]");
    ExitCode::from(2)
}
