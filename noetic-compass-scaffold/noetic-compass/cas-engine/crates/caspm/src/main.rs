use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use cas_engine::language::compile_file;
use casc_syntax::{parse_file as parse_frontend_file, AstNode};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Deserialize, Serialize)]
struct PackageSection {
    #[serde(rename = "name")]
    _name: String,
    #[serde(rename = "version")]
    _version: String,
    entry: String,
}

#[derive(Debug, Deserialize, Serialize, Default)]
struct DependencySpec {
    path: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct CasManifest {
    package: PackageSection,
    #[serde(default)]
    dependencies: BTreeMap<String, DependencySpec>,
}

#[derive(Debug, Serialize)]
struct LockEntry {
    path: String,
    sha256: String,
}

#[derive(Debug, Serialize)]
struct LockFile {
    package: String,
    version: String,
    entry: String,
    files: Vec<LockEntry>,
}

fn load_manifest(path: impl AsRef<Path>) -> Result<(PathBuf, CasManifest), String> {
    let path = path.as_ref();
    let manifest_path = if path.is_dir() {
        let upper = path.join("Cas.toml");
        if upper.exists() {
            upper
        } else {
            path.join("caspkg.toml")
        }
    } else {
        path.to_path_buf()
    };
    let raw = fs::read_to_string(&manifest_path)
        .map_err(|error| format!("failed to read {}: {error}", manifest_path.display()))?;
    let manifest: CasManifest = toml::from_str(&raw)
        .map_err(|error| format!("failed to parse {}: {error}", manifest_path.display()))?;
    Ok((manifest_path, manifest))
}

fn collect_imports(
    node: &AstNode,
    module_dir: &Path,
    seen: &mut BTreeSet<PathBuf>,
) -> Result<(), String> {
    match node {
        AstNode::UseStatement(stmt) => {
            let candidate = module_dir
                .join(&stmt.path)
                .canonicalize()
                .map_err(|error| {
                    format!(
                        "failed to resolve import {}: {error}",
                        module_dir.join(&stmt.path).display()
                    )
                })?;
            if seen.insert(candidate.clone()) {
                let ast = parse_frontend_file(&candidate)
                    .map_err(|error| format!("failed to parse {}: {error}", candidate.display()))?;
                let next_dir = candidate.parent().unwrap_or(module_dir);
                collect_imports(&ast, next_dir, seen)?;
            }
            Ok(())
        }
        AstNode::Program { statements } => {
            for statement in statements {
                collect_imports(statement, module_dir, seen)?;
            }
            Ok(())
        }
        AstNode::ExportStatement(stmt) => collect_imports(&stmt.statement, module_dir, seen),
        AstNode::LetStatement(stmt) => collect_imports(&stmt.expr, module_dir, seen),
        AstNode::FunctionDef(function) => collect_imports(&function.body, module_dir, seen),
        AstNode::RpmCall { expr } => collect_imports(expr, module_dir, seen),
        AstNode::CallExpr { args, .. } => {
            for arg in args {
                collect_imports(arg, module_dir, seen)?;
            }
            Ok(())
        }
        AstNode::BinaryExpr { left, right, .. } => {
            collect_imports(left, module_dir, seen)?;
            collect_imports(right, module_dir, seen)
        }
        _ => Ok(()),
    }
}

fn package_files(
    manifest_path: &Path,
    manifest: &CasManifest,
) -> Result<(PathBuf, BTreeSet<PathBuf>), String> {
    let root = manifest_path
        .parent()
        .ok_or_else(|| "manifest path had no parent directory".to_string())?;
    for (name, spec) in &manifest.dependencies {
        if let Some(rel_path) = &spec.path {
            let dep_path = root.join(rel_path);
            if !dep_path.exists() {
                return Err(format!(
                    "dependency {name} points to missing path {}",
                    dep_path.display()
                ));
            }
        }
    }
    let entry = root
        .join(&manifest.package.entry)
        .canonicalize()
        .map_err(|error| {
            format!(
                "failed to resolve entry {}: {error}",
                root.join(&manifest.package.entry).display()
            )
        })?;
    let artifact = compile_file(&entry);
    if !artifact.valid {
        return Err(artifact
            .error
            .unwrap_or_else(|| format!("failed to compile {}", entry.display())));
    }
    let ast = parse_frontend_file(&entry)
        .map_err(|error| format!("failed to parse {}: {error}", entry.display()))?;
    let mut seen = BTreeSet::new();
    seen.insert(entry.clone());
    collect_imports(&ast, entry.parent().unwrap_or(root), &mut seen)?;
    Ok((entry, seen))
}

fn hash_file(path: &Path) -> Result<String, String> {
    let bytes =
        fs::read(path).map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!("{:x}", hasher.finalize()))
}

fn check_package(path: impl AsRef<Path>) -> Result<serde_json::Value, String> {
    let (manifest_path, manifest) = load_manifest(path)?;
    let root = manifest_path
        .parent()
        .ok_or_else(|| "manifest path had no parent directory".to_string())?;
    let entry = root.join(&manifest.package.entry);
    let artifact = compile_file(entry);
    Ok(artifact.to_json())
}

fn graph_package(path: impl AsRef<Path>) -> Result<serde_json::Value, String> {
    let (manifest_path, manifest) = load_manifest(path)?;
    let (entry, files) = package_files(&manifest_path, &manifest)?;
    Ok(serde_json::json!({
        "package": manifest.package._name,
        "version": manifest.package._version,
        "entry": entry.display().to_string(),
        "files": files.into_iter().map(|path| path.display().to_string()).collect::<Vec<_>>(),
    }))
}

fn lock_package(path: impl AsRef<Path>) -> Result<serde_json::Value, String> {
    let (manifest_path, manifest) = load_manifest(path)?;
    let (entry, files) = package_files(&manifest_path, &manifest)?;
    let mut entries = Vec::new();
    for path in files {
        entries.push(LockEntry {
            path: path.display().to_string(),
            sha256: hash_file(&path)?,
        });
    }
    let lock = LockFile {
        package: manifest.package._name.clone(),
        version: manifest.package._version.clone(),
        entry: entry.display().to_string(),
        files: entries,
    };
    let lock_path = manifest_path.parent().unwrap().join("caspkg.lock.json");
    fs::write(&lock_path, serde_json::to_string_pretty(&lock).unwrap())
        .map_err(|error| format!("failed to write {}: {error}", lock_path.display()))?;
    Ok(serde_json::json!({
        "wrote": lock_path.display().to_string(),
        "package": lock.package,
        "version": lock.version,
    }))
}

fn add_dependency(
    path: impl AsRef<Path>,
    dependency_name: &str,
    dependency_path: impl AsRef<Path>,
) -> Result<serde_json::Value, String> {
    let (manifest_path, mut manifest) = load_manifest(path)?;
    let manifest_dir = manifest_path
        .parent()
        .ok_or_else(|| "manifest path had no parent directory".to_string())?;
    let dependency_path = dependency_path.as_ref();
    let resolved_dependency = if dependency_path.is_absolute() {
        dependency_path.to_path_buf()
    } else {
        manifest_dir.join(dependency_path)
    };
    if !resolved_dependency.exists() {
        return Err(format!(
            "dependency path does not exist: {}",
            resolved_dependency.display()
        ));
    }
    let relative = resolved_dependency
        .strip_prefix(manifest_dir)
        .map(PathBuf::from)
        .unwrap_or_else(|_| resolved_dependency.clone());
    manifest.dependencies.insert(
        dependency_name.to_string(),
        DependencySpec {
            path: Some(relative.display().to_string().replace('\\', "/")),
        },
    );
    let encoded = toml::to_string_pretty(&manifest).map_err(|error| {
        format!(
            "failed to encode manifest {}: {error}",
            manifest_path.display()
        )
    })?;
    fs::write(&manifest_path, encoded)
        .map_err(|error| format!("failed to write {}: {error}", manifest_path.display()))?;
    Ok(serde_json::json!({
        "updated": manifest_path.display().to_string(),
        "dependency": dependency_name,
        "path": manifest
            .dependencies
            .get(dependency_name)
            .and_then(|spec| spec.path.clone())
            .unwrap_or_default(),
    }))
}

fn create_package(root: impl AsRef<Path>, name: &str) -> Result<PathBuf, String> {
    let root = root.as_ref().join(name);
    fs::create_dir_all(root.join("src"))
        .map_err(|error| format!("failed to create {}: {error}", root.display()))?;
    let manifest = format!(
        "[package]\nname = \"{name}\"\nversion = \"0.1.0\"\nentry = \"src/main.cas\"\n\n[dependencies]\n"
    );
    let main_cas = format!(
        "# {name} entry\nlet foundation: state[C] = CO-2^C_{{F2}};\nlet outcome: state[E] = CO-5^E_{{F4}};\nfoundation -> outcome\n"
    );
    fs::write(root.join("Cas.toml"), manifest)
        .map_err(|error| format!("failed to write manifest: {error}"))?;
    fs::write(root.join("src").join("main.cas"), main_cas)
        .map_err(|error| format!("failed to write entry source: {error}"))?;
    Ok(root)
}

fn print_usage() {
    eprintln!("usage:");
    eprintln!("  caspm new <name> [root]");
    eprintln!("  caspm check [path-to-package-or-manifest]");
    eprintln!("  caspm run [path-to-package-or-manifest]");
    eprintln!("  caspm graph [path-to-package-or-manifest]");
    eprintln!("  caspm lock [path-to-package-or-manifest]");
    eprintln!("  caspm add [path-to-package-or-manifest] <dependency-name> <dependency-path>");
}

fn main() -> ExitCode {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else {
        print_usage();
        return ExitCode::from(2);
    };

    match command.as_str() {
        "new" => {
            let Some(name) = args.next() else {
                print_usage();
                return ExitCode::from(2);
            };
            let root = args
                .next()
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            match create_package(root, &name) {
                Ok(path) => {
                    println!("created CAS package at {}", path.display());
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::from(1)
                }
            }
        }
        "check" | "run" => {
            let path = args
                .next()
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            match check_package(path) {
                Ok(json) => {
                    println!("{}", serde_json::to_string_pretty(&json).unwrap());
                    if json["valid"].as_bool().unwrap_or(false) {
                        ExitCode::SUCCESS
                    } else {
                        ExitCode::from(1)
                    }
                }
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::from(1)
                }
            }
        }
        "graph" => {
            let path = args
                .next()
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            match graph_package(path) {
                Ok(json) => {
                    println!("{}", serde_json::to_string_pretty(&json).unwrap());
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::from(1)
                }
            }
        }
        "lock" => {
            let path = args
                .next()
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            match lock_package(path) {
                Ok(json) => {
                    println!("{}", serde_json::to_string_pretty(&json).unwrap());
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::from(1)
                }
            }
        }
        "add" => {
            let path = args
                .next()
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            let Some(dependency_name) = args.next() else {
                print_usage();
                return ExitCode::from(2);
            };
            let Some(dependency_path) = args.next() else {
                print_usage();
                return ExitCode::from(2);
            };
            match add_dependency(path, &dependency_name, PathBuf::from(dependency_path)) {
                Ok(json) => {
                    println!("{}", serde_json::to_string_pretty(&json).unwrap());
                    ExitCode::SUCCESS
                }
                Err(error) => {
                    eprintln!("{error}");
                    ExitCode::from(1)
                }
            }
        }
        _ => {
            print_usage();
            ExitCode::from(2)
        }
    }
}
