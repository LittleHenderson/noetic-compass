//! Shared IR and runtime value model for the CAS compiler toolchain.
//!
//! This crate intentionally sits between the syntax frontend and the
//! language/VM layer so CLI tools and engine code can speak the same
//! bytecode/result format without duplicating the public shape.

use casc_syntax::{AstNode, LexToken, TypeInfo};
use serde::Serialize;
use serde_json::{json, Value as JsonValue};

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StateValue {
    pub operator: u8,
    pub domain: String,
    pub drive: Option<u8>,
    pub domain_explicit: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RelationValue {
    pub relation: &'static str,
    pub source: StateValue,
    pub target: StateValue,
    pub admissible: bool,
    pub domain_descent_ok: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FractalValue {
    pub sequence: Vec<u8>,
    pub composed_operator: u8,
    pub domain: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RpmValue {
    pub drive: Option<u8>,
    pub completeness: String,
    pub chain: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FunctionValue {
    pub name: String,
    pub params: Vec<String>,
    pub param_types: Vec<TypeInfo>,
    pub return_type: TypeInfo,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ModuleValue {
    pub path: String,
    pub exports: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct MetaSetValue {
    pub name: String,
    pub elements: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct MetaSymbolValue {
    pub name: String,
    pub symbol_kind: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CardinalityValue {
    pub set: String,
    pub value: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct MetaAssertionValue {
    pub operator: String,
    pub holds: bool,
    pub message: String,
    pub left: Box<Value>,
    pub right: Box<Value>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Value {
    State(StateValue),
    Relation(RelationValue),
    Fractal(FractalValue),
    Rpm(RpmValue),
    Binding { name: String, value: Box<Value> },
    Function(FunctionValue),
    Module(ModuleValue),
    Program(Vec<Value>),
    String(String),
    Number(i64),
    Drive(u8),
    MetaSet(MetaSetValue),
    MetaSymbol(MetaSymbolValue),
    Cardinality(CardinalityValue),
    MetaAssertion(MetaAssertionValue),
}

impl Value {
    pub fn to_json(&self) -> JsonValue {
        match self {
            Self::State(state) => json!({
                "kind": "state",
                "dominant_state": format!("{}{}", state.domain, state.operator),
                "dominant_operator": format!("CO-{}", state.operator),
                "dominant_domain": state.domain,
                "dominant_drive": state.drive.map(|drive| format!("F{drive}")),
            }),
            Self::Relation(value) => json!({
                "kind": "relation",
                "relation": value.relation,
                "admissible": value.admissible,
                "domain_descent_ok": value.domain_descent_ok,
                "source": Value::State(value.source.clone()).to_json(),
                "target": Value::State(value.target.clone()).to_json(),
            }),
            Self::Fractal(value) => json!({
                "kind": "fractal",
                "sequence": value.sequence,
                "composed_operator": format!("CO-{}", value.composed_operator),
                "orbit_length": value.sequence.len(),
                "domain": value.domain,
            }),
            Self::Rpm(value) => json!({
                "kind": "rpm",
                "drive": value.drive.map(|drive| format!("F{drive}")),
                "completeness": value.completeness,
                "chain": value.chain,
            }),
            Self::Binding { name, value } => json!({
                "kind": "binding",
                "name": name,
                "value": value.to_json(),
            }),
            Self::Function(value) => json!({
                "kind": "function",
                "name": value.name,
                "params": value.params,
                "param_types": value.param_types,
                "return_type": value.return_type,
            }),
            Self::Module(value) => json!({
                "kind": "module",
                "path": value.path,
                "exports": value.exports,
            }),
            Self::Program(results) => json!({
                "kind": "program",
                "results": results.iter().map(Value::to_json).collect::<Vec<_>>(),
                "final_result": results.last().map(Value::to_json),
            }),
            Self::String(value) => json!(value),
            Self::Number(value) => json!(value),
            Self::Drive(drive) => json!({"kind": "drive", "drive": format!("F{drive}")}),
            Self::MetaSet(value) => json!({
                "kind": "meta_set",
                "name": value.name,
                "cardinality": value.elements.len(),
                "elements": value.elements,
            }),
            Self::MetaSymbol(value) => json!({
                "kind": "meta_symbol",
                "name": value.name,
                "symbol_kind": value.symbol_kind,
            }),
            Self::Cardinality(value) => json!({
                "kind": "cardinality",
                "set": value.set,
                "value": value.value,
            }),
            Self::MetaAssertion(value) => json!({
                "kind": "meta_assertion",
                "operator": value.operator,
                "holds": value.holds,
                "message": value.message,
                "left": value.left.to_json(),
                "right": value.right.to_json(),
            }),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "opcode", content = "arg", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Instruction {
    PushState {
        operator: u8,
        domain: String,
        drive: Option<u8>,
        domain_explicit: bool,
    },
    PushDrive(u8),
    PushFractal(Vec<u8>),
    PushString(String),
    PushNumber(i64),
    PushMetaSet {
        name: String,
    },
    PushMetaSymbol {
        name: String,
        symbol_kind: String,
    },
    Cardinality,
    MetaAssert {
        op: String,
    },
    LoadVar(String),
    StoreVar {
        name: String,
        annotation: Option<TypeInfo>,
    },
    Rpm,
    Call {
        name: String,
        argc: usize,
    },
    Arrow,
    Times,
    Divide,
    Circ,
    DefFunc {
        name: String,
        params: Vec<String>,
        param_types: Vec<TypeInfo>,
        return_type: Option<TypeInfo>,
        body: Vec<Instruction>,
    },
    Import(String),
    ExportName(String),
    EmitResult,
    BuildProgramResult,
}

impl Instruction {
    pub fn to_json(&self) -> JsonValue {
        match self {
            Self::PushState {
                operator,
                domain,
                drive,
                domain_explicit,
            } => {
                json!({"opcode": "PUSH_STATE", "arg": {"operator": operator, "domain": domain, "drive": drive, "domain_explicit": domain_explicit}})
            }
            Self::PushDrive(drive) => json!({"opcode": "PUSH_DRIVE", "arg": drive}),
            Self::PushFractal(sequence) => json!({"opcode": "PUSH_FRACTAL", "arg": sequence}),
            Self::PushString(value) => json!({"opcode": "PUSH_STRING", "arg": value}),
            Self::PushNumber(value) => json!({"opcode": "PUSH_NUMBER", "arg": value}),
            Self::PushMetaSet { name } => {
                json!({"opcode": "PUSH_META_SET", "arg": {"name": name}})
            }
            Self::PushMetaSymbol { name, symbol_kind } => json!({
                "opcode": "PUSH_META_SYMBOL",
                "arg": {"name": name, "symbol_kind": symbol_kind}
            }),
            Self::Cardinality => json!({"opcode": "CARDINALITY", "arg": JsonValue::Null}),
            Self::MetaAssert { op } => json!({"opcode": "META_ASSERT", "arg": {"op": op}}),
            Self::LoadVar(name) => json!({"opcode": "LOAD_VAR", "arg": name}),
            Self::StoreVar { name, annotation } => {
                json!({"opcode": "STORE_VAR", "arg": {"name": name, "annotation": annotation}})
            }
            Self::Rpm => json!({"opcode": "RPM", "arg": JsonValue::Null}),
            Self::Call { name, argc } => {
                json!({"opcode": "CALL", "arg": {"name": name, "argc": argc}})
            }
            Self::Arrow => json!({"opcode": "ARROW", "arg": JsonValue::Null}),
            Self::Times => json!({"opcode": "TIMES", "arg": JsonValue::Null}),
            Self::Divide => json!({"opcode": "DIVIDE", "arg": JsonValue::Null}),
            Self::Circ => json!({"opcode": "CIRC", "arg": JsonValue::Null}),
            Self::DefFunc {
                name,
                params,
                param_types,
                return_type,
                body,
            } => json!({
                "opcode": "DEF_FUNC",
                "arg": {
                    "name": name,
                    "params": params,
                    "param_types": param_types,
                    "return_type": return_type,
                    "body": body.iter().map(Instruction::to_json).collect::<Vec<_>>()
                }
            }),
            Self::Import(path) => json!({"opcode": "IMPORT", "arg": path}),
            Self::ExportName(name) => json!({"opcode": "EXPORT_NAME", "arg": name}),
            Self::EmitResult => json!({"opcode": "EMIT_RESULT", "arg": JsonValue::Null}),
            Self::BuildProgramResult => {
                json!({"opcode": "BUILD_PROGRAM_RESULT", "arg": JsonValue::Null})
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompilationArtifact {
    pub source: String,
    pub tokens: Vec<LexToken>,
    pub ast: Option<AstNode>,
    pub type_info: Option<TypeInfo>,
    pub bytecode: Vec<Instruction>,
    pub result: Option<Value>,
    pub warnings: Vec<String>,
    pub valid: bool,
    pub error: Option<String>,
}

impl CompilationArtifact {
    pub fn to_json(&self) -> JsonValue {
        json!({
            "source": self.source,
            "valid": self.valid,
            "error": self.error,
            "engine": "rust-native+cas-engine",
            "warnings": self.warnings,
            "tokens": self.tokens,
            "ast": self.ast,
            "type": self.type_info,
            "bytecode": self.bytecode.iter().map(Instruction::to_json).collect::<Vec<_>>(),
            "result": self.result.as_ref().map(Value::to_json),
        })
    }
}
