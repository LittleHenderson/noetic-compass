//! Rust-native CAS language compiler/interpreter.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use casc_ir::{
    CompilationArtifact, FractalValue, FunctionValue, Instruction, ModuleValue, RelationValue,
    RpmValue, StateValue, Value,
};
use casc_syntax::{self as syntax, LanguageError as SyntaxLanguageError};
use casc_types::{
    InferCtx as HmInferCtx, InferenceError as HmInferenceError, MonoType, PrimitiveType, Scheme,
    TypeEnv as HmTypeEnv,
};
use thiserror::Error;

use crate::ontology::{CognitiveOperator, CoreDrive, Domain};

pub const CAS_GRAMMAR_BNF: &str = r#"<program>          ::= <statement> (";" <statement>)* ;
<statement>        ::= <export_stmt> | <let_stmt> | <fn_stmt> | <use_stmt> | <expression> ;
<export_stmt>      ::= "export" (<let_stmt> | <fn_stmt>) ;
<let_stmt>         ::= "let" <ident> (":" <type_expr>)? "=" <expression> ;
<fn_stmt>          ::= "fn" <ident> "(" <typed_param_list>? ")" (":" <type_expr>)? "=" <expression> ;
<use_stmt>         ::= "use" <string> ;
<typed_param_list> ::= <typed_param> ("," <typed_param>)* ;
<typed_param>      ::= <ident> (":" <type_expr>)? ;
<type_expr>        ::= <type_name> ("[" <domain_list> "]")? ;
<type_name>        ::= "state" | "drive" | "string" | "fractal" | "rpm" | "relation" | "program" | "any" ;
<domain_list>      ::= <domain> ("," <domain>)* ;
<expression>       ::= <relation> ;
<relation>         ::= <composition> (("->") <composition>)* ;
<composition>      ::= <primary> (("*" | "/" | "circ") <primary>)* ;
<primary>          ::= <state> | <state_ref> | <drive_ref> | <rpm_call> | <phi_literal> | <call> | <ident> | <string> | "(" <expression> ")" ;
<call>             ::= <ident> "(" <arg_list>? ")" ;
<arg_list>         ::= <expression> ("," <expression>)* ;
<rpm_call>         ::= "RPM" "(" (<state> | <state_ref> | <drive_ref>) ")" ;
<phi_literal>      ::= ("Phi" | "Φ") ("<" | "⟨") <sequence> (">" | "⟩") ;
<sequence>         ::= <digit> (":" <digit>)* ;
<state>            ::= <operator> "^" <domain> ("_{" <drive_ref> "}")? ;
<state_ref>        ::= <domain> <digit> ;
<operator>         ::= "CO-" <digit> ;
<drive_ref>        ::= "F" <drive_digit> ;"#;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage {
    Lexing,
    Parsing,
    Typecheck,
    Lowering,
    Execution,
}

impl Stage {
    fn as_str(self) -> &'static str {
        match self {
            Self::Lexing => "lexing",
            Self::Parsing => "parsing",
            Self::Typecheck => "typecheck",
            Self::Lowering => "lowering",
            Self::Execution => "execution",
        }
    }
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
#[error("{stage}{position}: {message}")]
pub struct LanguageError {
    stage: &'static str,
    position: String,
    message: String,
}

impl LanguageError {
    fn new(stage: Stage, message: impl Into<String>, position: Option<usize>) -> Self {
        Self {
            stage: stage.as_str(),
            position: position.map(|p| format!("@{p}")).unwrap_or_default(),
            message: message.into(),
        }
    }
}

pub type TokenKind = syntax::TokenKind;
pub type LexToken = syntax::LexToken;
pub type TypeKind = syntax::TypeKind;
pub type TypeInfo = syntax::TypeInfo;
pub type LetStatement = syntax::LetStatement;
pub type FunctionDef = syntax::FunctionDef;
pub type UseStatement = syntax::UseStatement;
pub type ExportStatement = syntax::ExportStatement;
pub type BinaryOp = syntax::BinaryOp;
pub type AstNode = syntax::AstNode;

fn parse_domain_code(code: &str) -> Option<Domain> {
    match code {
        "P" => Some(Domain::Principled),
        "C" => Some(Domain::Cognitive),
        "E" => Some(Domain::Evaluative),
        "O" => Some(Domain::Operational),
        _ => None,
    }
}

fn parse_drive_number(number: u8) -> Result<CoreDrive, LanguageError> {
    CoreDrive::from_number(number).ok_or_else(|| {
        LanguageError::new(
            Stage::Typecheck,
            format!("drive number must be 1-7, got F{number}"),
            None,
        )
    })
}

fn parse_operator_index(index: u8) -> Result<CognitiveOperator, LanguageError> {
    CognitiveOperator::from_index(index as usize).ok_or_else(|| {
        LanguageError::new(
            Stage::Typecheck,
            format!("operator index must be 0-9, got {index}"),
            None,
        )
    })
}

fn stage_from_syntax(stage: &str) -> Stage {
    match stage {
        "lexing" => Stage::Lexing,
        "parsing" => Stage::Parsing,
        "typecheck" => Stage::Typecheck,
        "lowering" => Stage::Lowering,
        "execution" => Stage::Execution,
        _ => Stage::Parsing,
    }
}

fn language_error_from_syntax(error: SyntaxLanguageError) -> LanguageError {
    LanguageError::new(
        stage_from_syntax(error.stage_label()),
        error.message().to_string(),
        None,
    )
}

fn parse_source_via_syntax(source: &str) -> Result<(Vec<LexToken>, AstNode), LanguageError> {
    let tokens = syntax::lex(source).map_err(language_error_from_syntax)?;
    let ast = syntax::parse_tokens(tokens.clone()).map_err(language_error_from_syntax)?;
    Ok((tokens, ast))
}

pub fn lex(source: &str) -> Result<Vec<LexToken>, LanguageError> {
    syntax::lex(source).map_err(language_error_from_syntax)
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct FunctionSignature {
    param_types: Vec<TypeInfo>,
    return_type: TypeInfo,
    scheme: Option<Scheme>,
}

#[derive(Debug, Clone)]
struct TypeEnv {
    vars: HashMap<String, TypeInfo>,
    funcs: HashMap<String, FunctionSignature>,
    module_dir: Option<PathBuf>,
    import_stack: HashSet<PathBuf>,
    exports: HashSet<String>,
}

impl TypeEnv {
    fn new(module_dir: Option<PathBuf>) -> Self {
        Self {
            vars: HashMap::new(),
            funcs: HashMap::new(),
            module_dir,
            import_stack: HashSet::new(),
            exports: HashSet::new(),
        }
    }
}

fn format_type(info: &TypeInfo) -> String {
    let mut out = match info.kind {
        TypeKind::Any => "any",
        TypeKind::State => "state",
        TypeKind::Drive => "drive",
        TypeKind::String => "string",
        TypeKind::Fractal => "fractal",
        TypeKind::Rpm => "rpm",
        TypeKind::Relation => "relation",
        TypeKind::Program => "program",
    }
    .to_string();
    if !info.domains.is_empty() {
        out.push('[');
        out.push_str(&info.domains.join(","));
        out.push(']');
    }
    out
}

fn type_matches(actual: &TypeInfo, expected: &TypeInfo) -> bool {
    if actual.kind == TypeKind::Any || expected.kind == TypeKind::Any {
        return true;
    }
    if actual.kind != expected.kind {
        return false;
    }
    if expected.singular && !actual.singular {
        return false;
    }
    if !expected.domains.is_empty() && !actual.domains.is_empty() {
        return actual
            .domains
            .iter()
            .all(|domain| expected.domains.contains(domain));
    }
    true
}

fn assert_type(actual: &TypeInfo, expected: &TypeInfo, context: &str) -> Result<(), LanguageError> {
    if type_matches(actual, expected) {
        Ok(())
    } else {
        Err(LanguageError::new(
            Stage::Typecheck,
            format!(
                "{context}: expected {}, got {}",
                format_type(expected),
                format_type(actual)
            ),
            None,
        ))
    }
}

fn merge_expected_type(
    slot: &mut TypeInfo,
    expected: &TypeInfo,
    context: &str,
) -> Result<(), LanguageError> {
    if slot.kind == TypeKind::Any {
        *slot = expected.clone();
        Ok(())
    } else {
        assert_type(slot, expected, context)
    }
}

fn union_domains(left: &[String], right: &[String]) -> Vec<String> {
    let mut out: Vec<String> = left.iter().cloned().chain(right.iter().cloned()).collect();
    out.sort_by_key(|value| match value.as_str() {
        "P" => 0usize,
        "C" => 1usize,
        "E" => 2usize,
        "O" => 3usize,
        _ => 99usize,
    });
    out.dedup();
    out
}

fn hm_error_to_language(error: HmInferenceError) -> LanguageError {
    LanguageError::new(
        Stage::Typecheck,
        format!("hm inference failed: {error:?}"),
        None,
    )
}

fn hm_primitive_from_type_info(info: &TypeInfo) -> Option<PrimitiveType> {
    match info.kind {
        TypeKind::Any => None,
        TypeKind::State => Some(PrimitiveType::State),
        TypeKind::Drive => Some(PrimitiveType::Drive),
        TypeKind::String => Some(PrimitiveType::String),
        TypeKind::Fractal => Some(PrimitiveType::Fractal),
        TypeKind::Rpm => Some(PrimitiveType::Rpm),
        TypeKind::Relation => Some(PrimitiveType::Relation),
        TypeKind::Program => Some(PrimitiveType::Program),
    }
}

fn hm_type_from_type_info(info: &TypeInfo, ctx: &mut HmInferCtx) -> MonoType {
    hm_primitive_from_type_info(info)
        .map(MonoType::Primitive)
        .unwrap_or_else(|| ctx.fresh_var())
}

fn type_info_from_hm_primitive(kind: PrimitiveType, domains: Vec<String>) -> TypeInfo {
    let (kind, singular) = match kind {
        PrimitiveType::State => (TypeKind::State, true),
        PrimitiveType::Drive => (TypeKind::Drive, true),
        PrimitiveType::String => (TypeKind::String, true),
        PrimitiveType::Fractal => (TypeKind::Fractal, true),
        PrimitiveType::Rpm => (TypeKind::Rpm, true),
        PrimitiveType::Relation => (TypeKind::Relation, false),
        PrimitiveType::Program => (TypeKind::Program, false),
        PrimitiveType::Any => (TypeKind::Any, false),
    };
    TypeInfo::new(kind, domains, singular)
}

fn monomorphic_scheme(param_types: &[TypeInfo], return_type: &TypeInfo) -> Scheme {
    let mut next_var = 0u32;
    let mut fresh_or_primitive = |info: &TypeInfo| {
        hm_primitive_from_type_info(info)
            .map(MonoType::Primitive)
            .unwrap_or_else(|| {
                let var = next_var;
                next_var += 1;
                MonoType::Var(var)
            })
    };
    let params = param_types
        .iter()
        .map(&mut fresh_or_primitive)
        .collect::<Vec<_>>();
    let ret = fresh_or_primitive(return_type);
    Scheme {
        vars: (0..next_var).collect(),
        ty: MonoType::Function(params, Box::new(ret)),
    }
}

fn hm_builtin_scheme(name: &str) -> Option<Scheme> {
    let state = MonoType::Primitive(PrimitiveType::State);
    let string = MonoType::Primitive(PrimitiveType::String);
    let fractal = MonoType::Primitive(PrimitiveType::Fractal);
    let rpm = MonoType::Primitive(PrimitiveType::Rpm);
    match name {
        "dominant_state" | "dominant_domain" | "dominant_operator" => Some(Scheme {
            vars: Vec::new(),
            ty: MonoType::Function(vec![state], Box::new(string)),
        }),
        "compose" => Some(Scheme {
            vars: Vec::new(),
            ty: MonoType::Function(
                vec![
                    MonoType::Primitive(PrimitiveType::State),
                    MonoType::Primitive(PrimitiveType::State),
                ],
                Box::new(MonoType::Primitive(PrimitiveType::State)),
            ),
        }),
        "rpm_of" => Some(Scheme {
            vars: Vec::new(),
            ty: MonoType::Function(
                vec![MonoType::Primitive(PrimitiveType::State)],
                Box::new(rpm),
            ),
        }),
        "fractal" => Some(Scheme {
            vars: vec![0],
            ty: MonoType::Function(vec![MonoType::Var(0), MonoType::Var(0)], Box::new(fractal)),
        }),
        _ => None,
    }
}

fn hm_infer_expr(
    node: &AstNode,
    ctx: &mut HmInferCtx,
    env: &HmTypeEnv,
    locals: &HashMap<String, MonoType>,
) -> Result<MonoType, LanguageError> {
    match node {
        AstNode::StateLiteral { .. } => Ok(MonoType::Primitive(PrimitiveType::State)),
        AstNode::DriveLiteral { .. } => Ok(MonoType::Primitive(PrimitiveType::Drive)),
        AstNode::FractalLiteral { .. } => Ok(MonoType::Primitive(PrimitiveType::Fractal)),
        AstNode::StringLiteral { .. } => Ok(MonoType::Primitive(PrimitiveType::String)),
        AstNode::RpmCall { expr } => {
            let arg = hm_infer_expr(expr, ctx, env, locals)?;
            let state = MonoType::Primitive(PrimitiveType::State);
            let drive = MonoType::Primitive(PrimitiveType::Drive);
            if ctx.unify(&arg, &state).is_err() {
                ctx.unify(&arg, &drive).map_err(hm_error_to_language)?;
            }
            Ok(MonoType::Primitive(PrimitiveType::Rpm))
        }
        AstNode::Identifier { name } => {
            if let Some(local) = locals.get(name) {
                return Ok(local.clone());
            }
            if let Some(scheme) = env.get(name) {
                return Ok(ctx.instantiate(scheme));
            }
            Err(LanguageError::new(
                Stage::Typecheck,
                format!("undefined variable {name}"),
                None,
            ))
        }
        AstNode::CallExpr { callee, args } => {
            let callee_ty = if let Some(scheme) = hm_builtin_scheme(callee) {
                ctx.instantiate(&scheme)
            } else if let Some(scheme) = env.get(callee) {
                ctx.instantiate(scheme)
            } else {
                return Err(LanguageError::new(
                    Stage::Typecheck,
                    format!("undefined function {callee}"),
                    None,
                ));
            };
            let arg_types = args
                .iter()
                .map(|arg| hm_infer_expr(arg, ctx, env, locals))
                .collect::<Result<Vec<_>, _>>()?;
            let ret = ctx.fresh_var();
            let fn_ty = MonoType::Function(arg_types, Box::new(ret.clone()));
            ctx.unify(&callee_ty, &fn_ty)
                .map_err(hm_error_to_language)?;
            Ok(ctx.subst().apply(&ret))
        }
        AstNode::BinaryExpr { op, left, right } => {
            let left_ty = hm_infer_expr(left, ctx, env, locals)?;
            let right_ty = hm_infer_expr(right, ctx, env, locals)?;
            match op {
                BinaryOp::Arrow => {
                    let state = MonoType::Primitive(PrimitiveType::State);
                    ctx.unify(&left_ty, &state).map_err(hm_error_to_language)?;
                    ctx.unify(&right_ty, &state).map_err(hm_error_to_language)?;
                    Ok(MonoType::Primitive(PrimitiveType::Relation))
                }
                BinaryOp::Times | BinaryOp::Divide => {
                    let state = MonoType::Primitive(PrimitiveType::State);
                    ctx.unify(&left_ty, &state).map_err(hm_error_to_language)?;
                    ctx.unify(&right_ty, &state).map_err(hm_error_to_language)?;
                    Ok(MonoType::Primitive(PrimitiveType::State))
                }
                BinaryOp::Circ => Ok(MonoType::Primitive(PrimitiveType::Fractal)),
            }
        }
        AstNode::LetStatement(_)
        | AstNode::FunctionDef(_)
        | AstNode::UseStatement(_)
        | AstNode::ExportStatement(_)
        | AstNode::Program { .. } => Err(LanguageError::new(
            Stage::Typecheck,
            "hm inference only supports expression bodies",
            None,
        )),
    }
}

fn infer_function_scheme(function: &FunctionDef, env: &TypeEnv) -> Option<Scheme> {
    let mut hm_env = HmTypeEnv::default();
    for (name, signature) in &env.funcs {
        let scheme = signature
            .scheme
            .clone()
            .unwrap_or_else(|| monomorphic_scheme(&signature.param_types, &signature.return_type));
        hm_env.insert(name.clone(), scheme);
    }
    let mut ctx = HmInferCtx::default();
    let mut locals = HashMap::new();
    let mut param_tys = Vec::new();
    for (name, annotation) in function.params.iter().zip(function.param_types.iter()) {
        let ty = hm_type_from_type_info(annotation, &mut ctx);
        locals.insert(name.clone(), ty.clone());
        param_tys.push(ty);
    }
    let body_ty = hm_infer_expr(&function.body, &mut ctx, &hm_env, &locals).ok()?;
    let return_ty = if let Some(annotation) = &function.return_type {
        let annotated = hm_type_from_type_info(annotation, &mut ctx);
        ctx.unify(&body_ty, &annotated).ok()?;
        annotated
    } else {
        body_ty
    };
    Some(ctx.generalize(
        &hm_env,
        &MonoType::Function(param_tys, Box::new(ctx.subst().apply(&return_ty))),
    ))
}

fn infer_return_from_scheme(
    signature: &FunctionSignature,
    arg_types: &[TypeInfo],
) -> Option<TypeInfo> {
    let scheme = signature.scheme.as_ref()?;
    let mut ctx = HmInferCtx::default();
    let instantiated = ctx.instantiate(scheme);
    let MonoType::Function(expected_params, ret) = instantiated else {
        return None;
    };
    if expected_params.len() != arg_types.len() {
        return None;
    }
    for (expected, actual) in expected_params.iter().zip(arg_types.iter()) {
        let actual_ty = hm_type_from_type_info(actual, &mut ctx);
        ctx.unify(expected, &actual_ty).ok()?;
    }
    let resolved = ctx.subst().apply(&ret);
    let MonoType::Primitive(kind) = resolved else {
        return None;
    };
    let fallback_domains = match kind {
        PrimitiveType::State => arg_types
            .iter()
            .find(|arg| arg.kind == TypeKind::State && !arg.domains.is_empty())
            .map(|arg| arg.domains.clone())
            .unwrap_or_else(|| signature.return_type.domains.clone()),
        PrimitiveType::Relation => {
            arg_types
                .iter()
                .fold(signature.return_type.domains.clone(), |acc, arg| {
                    if arg.domains.is_empty() {
                        acc
                    } else {
                        union_domains(&acc, &arg.domains)
                    }
                })
        }
        _ => signature.return_type.domains.clone(),
    };
    Some(type_info_from_hm_primitive(kind, fallback_domains))
}

fn constrain_expr(
    node: &AstNode,
    expected: &TypeInfo,
    params: &mut HashMap<String, TypeInfo>,
    env: &TypeEnv,
) -> Result<(), LanguageError> {
    match node {
        AstNode::Identifier { name } => {
            if let Some(slot) = params.get_mut(name) {
                merge_expected_type(slot, expected, &format!("inferred contract for {name}"))?;
            }
        }
        AstNode::CallExpr { callee, args } => match callee.as_str() {
            "dominant_state" | "dominant_domain" | "dominant_operator" => {
                if let Some(arg) = args.first() {
                    constrain_expr(
                        arg,
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        params,
                        env,
                    )?;
                }
            }
            "compose" => {
                for arg in args {
                    constrain_expr(
                        arg,
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        params,
                        env,
                    )?;
                }
            }
            "rpm_of" => {}
            "fractal" => {
                for arg in args {
                    constrain_expr(
                        arg,
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        params,
                        env,
                    )?;
                }
            }
            _ => {
                if let Some(signature) = env.funcs.get(callee) {
                    for (arg, expected_param) in args.iter().zip(signature.param_types.iter()) {
                        if expected_param.kind != TypeKind::Any {
                            constrain_expr(arg, expected_param, params, env)?;
                        }
                    }
                }
            }
        },
        AstNode::BinaryExpr { op, left, right } => match op {
            BinaryOp::Arrow | BinaryOp::Times | BinaryOp::Divide | BinaryOp::Circ => {
                constrain_expr(
                    left,
                    &TypeInfo::new(TypeKind::State, Vec::new(), true),
                    params,
                    env,
                )?;
                constrain_expr(
                    right,
                    &TypeInfo::new(TypeKind::State, Vec::new(), true),
                    params,
                    env,
                )?;
            }
        },
        AstNode::RpmCall { expr } => {
            let _ = expected;
            constrain_expr(
                expr,
                &TypeInfo::new(TypeKind::State, Vec::new(), true),
                params,
                env,
            )?;
        }
        AstNode::StateLiteral { .. }
        | AstNode::DriveLiteral { .. }
        | AstNode::FractalLiteral { .. }
        | AstNode::StringLiteral { .. }
        | AstNode::LetStatement(_)
        | AstNode::FunctionDef(_)
        | AstNode::UseStatement(_)
        | AstNode::ExportStatement(_)
        | AstNode::Program { .. } => {}
    }
    Ok(())
}

fn infer(
    node: &AstNode,
    warnings: &mut Vec<String>,
    env: &mut TypeEnv,
) -> Result<TypeInfo, LanguageError> {
    match node {
        AstNode::StateLiteral {
            operator,
            domain,
            drive,
        } => {
            let _ = parse_operator_index(*operator)?;
            let _ = parse_domain_code(domain).ok_or_else(|| {
                LanguageError::new(
                    Stage::Typecheck,
                    format!("domain must be one of [P, C, E, O], got {domain}"),
                    None,
                )
            })?;
            if let Some(drive) = drive {
                let _ = parse_drive_number(*drive)?;
            }
            Ok(TypeInfo::new(TypeKind::State, vec![domain.clone()], true))
        }
        AstNode::DriveLiteral { drive } => {
            let _ = parse_drive_number(*drive)?;
            Ok(TypeInfo::new(TypeKind::Drive, Vec::new(), true))
        }
        AstNode::FractalLiteral { sequence } => {
            if sequence.is_empty() {
                return Err(LanguageError::new(
                    Stage::Typecheck,
                    "fractal sequence cannot be empty",
                    None,
                ));
            }
            for operator in sequence {
                let _ = parse_operator_index(*operator)?;
            }
            Ok(TypeInfo::new(TypeKind::Fractal, Vec::new(), true))
        }
        AstNode::StringLiteral { .. } => Ok(TypeInfo::new(TypeKind::String, Vec::new(), true)),
        AstNode::Identifier { name } => env.vars.get(name).cloned().ok_or_else(|| {
            LanguageError::new(Stage::Typecheck, format!("undefined variable {name}"), None)
        }),
        AstNode::RpmCall { expr } => {
            let inner = infer(expr, warnings, env)?;
            if !matches!(
                inner.kind,
                TypeKind::State | TypeKind::Drive | TypeKind::Any
            ) {
                return Err(LanguageError::new(
                    Stage::Typecheck,
                    "RPM(...) accepts only a state or drive literal",
                    None,
                ));
            }
            Ok(TypeInfo::new(TypeKind::Rpm, Vec::new(), true))
        }
        AstNode::CallExpr { callee, args } => {
            let arg_types = args
                .iter()
                .map(|arg| infer(arg, warnings, env))
                .collect::<Result<Vec<_>, _>>()?;
            match callee.as_str() {
                "dominant_state" | "dominant_domain" | "dominant_operator" => {
                    if arg_types.len() != 1 {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            format!(
                                "builtin {callee} expects 1 argument, got {}",
                                arg_types.len()
                            ),
                            None,
                        ));
                    }
                    assert_type(
                        &arg_types[0],
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        &format!("builtin {callee}"),
                    )?;
                    Ok(TypeInfo::new(TypeKind::String, Vec::new(), true))
                }
                "compose" => {
                    if arg_types.len() != 2 {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            format!(
                                "builtin compose expects 2 arguments, got {}",
                                arg_types.len()
                            ),
                            None,
                        ));
                    }
                    assert_type(
                        &arg_types[0],
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        "builtin compose arg1",
                    )?;
                    assert_type(
                        &arg_types[1],
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        "builtin compose arg2",
                    )?;
                    if !arg_types[0].domains.is_empty()
                        && !arg_types[1].domains.is_empty()
                        && arg_types[0].domains != arg_types[1].domains
                    {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            "builtin compose requires both states to share a domain",
                            None,
                        ));
                    }
                    Ok(TypeInfo::new(
                        TypeKind::State,
                        if !arg_types[0].domains.is_empty() {
                            arg_types[0].domains.clone()
                        } else {
                            arg_types[1].domains.clone()
                        },
                        true,
                    ))
                }
                "rpm_of" => {
                    if arg_types.len() != 1 {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            format!("builtin rpm_of expects 1 argument, got {}", arg_types.len()),
                            None,
                        ));
                    }
                    if !matches!(
                        arg_types[0].kind,
                        TypeKind::State | TypeKind::Drive | TypeKind::Any
                    ) {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            "builtin rpm_of expects a state or drive argument",
                            None,
                        ));
                    }
                    Ok(TypeInfo::new(TypeKind::Rpm, Vec::new(), true))
                }
                "fractal" => {
                    if arg_types.len() < 2 {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            "builtin fractal expects at least two arguments",
                            None,
                        ));
                    }
                    for argument in &arg_types {
                        if !matches!(
                            argument.kind,
                            TypeKind::State | TypeKind::Fractal | TypeKind::Any
                        ) {
                            return Err(LanguageError::new(
                                Stage::Typecheck,
                                "builtin fractal expects state or fractal arguments",
                                None,
                            ));
                        }
                    }
                    Ok(TypeInfo::new(TypeKind::Fractal, Vec::new(), true))
                }
                _ => {
                    let signature = env.funcs.get(callee).cloned().ok_or_else(|| {
                        LanguageError::new(
                            Stage::Typecheck,
                            format!("undefined function {callee}"),
                            None,
                        )
                    })?;
                    if signature.param_types.len() != arg_types.len() {
                        return Err(LanguageError::new(
                            Stage::Typecheck,
                            format!(
                                "function {callee} expects {} arguments, got {}",
                                signature.param_types.len(),
                                arg_types.len()
                            ),
                            None,
                        ));
                    }
                    for (index, (actual, expected)) in arg_types
                        .iter()
                        .zip(signature.param_types.iter())
                        .enumerate()
                    {
                        assert_type(
                            actual,
                            expected,
                            &format!("function {callee} argument {}", index + 1),
                        )?;
                    }
                    if signature.scheme.is_none()
                        && (signature
                            .param_types
                            .iter()
                            .any(|param| param.kind == TypeKind::Any)
                            || signature.return_type.kind == TypeKind::Any)
                    {
                        warnings.push(format!("function {callee}(...) contains inferred any-typed contracts; prefer explicit annotations"));
                    }
                    Ok(infer_return_from_scheme(&signature, &arg_types)
                        .unwrap_or(signature.return_type))
                }
            }
        }
        AstNode::BinaryExpr { op, left, right } => {
            let left_type = infer(left, warnings, env)?;
            let right_type = infer(right, warnings, env)?;
            match op {
                BinaryOp::Times | BinaryOp::Divide | BinaryOp::Circ => match op {
                    BinaryOp::Circ => {
                        if !matches!(
                            left_type.kind,
                            TypeKind::State | TypeKind::Fractal | TypeKind::Any
                        ) {
                            return Err(LanguageError::new(
                                Stage::Typecheck,
                                "circ expects a state or fractal left operand",
                                None,
                            ));
                        }
                        if !matches!(
                            right_type.kind,
                            TypeKind::State | TypeKind::Fractal | TypeKind::Any
                        ) {
                            return Err(LanguageError::new(
                                Stage::Typecheck,
                                "circ expects a state or fractal right operand",
                                None,
                            ));
                        }
                        Ok(TypeInfo::new(TypeKind::Fractal, Vec::new(), true))
                    }
                    BinaryOp::Times | BinaryOp::Divide => {
                        assert_type(
                            &left_type,
                            &TypeInfo::new(TypeKind::State, Vec::new(), true),
                            "composition left operand",
                        )?;
                        assert_type(
                            &right_type,
                            &TypeInfo::new(TypeKind::State, Vec::new(), true),
                            "composition right operand",
                        )?;
                        if !left_type.domains.is_empty()
                            && !right_type.domains.is_empty()
                            && left_type.domains != right_type.domains
                        {
                            return Err(LanguageError::new(
                                Stage::Typecheck,
                                "composition requires both states to share a domain",
                                None,
                            ));
                        }
                        Ok(TypeInfo::new(
                            TypeKind::State,
                            if !left_type.domains.is_empty() {
                                left_type.domains
                            } else {
                                right_type.domains
                            },
                            true,
                        ))
                    }
                    BinaryOp::Arrow => unreachable!(),
                },
                BinaryOp::Arrow => {
                    assert_type(
                        &left_type,
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        "relation left operand",
                    )?;
                    assert_type(
                        &right_type,
                        &TypeInfo::new(TypeKind::State, Vec::new(), true),
                        "relation right operand",
                    )?;
                    if left_type.domains.len() == 1 && right_type.domains.len() == 1 {
                        let left_domain = parse_domain_code(&left_type.domains[0]).unwrap();
                        let right_domain = parse_domain_code(&right_type.domains[0]).unwrap();
                        if left_domain.index() > right_domain.index() {
                            return Err(LanguageError::new(
                                Stage::Typecheck,
                                format!(
                                    "domain descent violated: {} cannot descend to {}",
                                    left_type.domains[0], right_type.domains[0]
                                ),
                                None,
                            ));
                        }
                    }
                    Ok(TypeInfo::new(
                        TypeKind::Relation,
                        union_domains(&left_type.domains, &right_type.domains),
                        false,
                    ))
                }
            }
        }
        AstNode::LetStatement(stmt) => {
            let expr_type = infer(&stmt.expr, warnings, env)?;
            let stored = if let Some(annotation) = &stmt.annotation {
                assert_type(&expr_type, annotation, &format!("binding {}", stmt.name))?;
                annotation.clone()
            } else {
                expr_type
            };
            env.vars.insert(stmt.name.clone(), stored);
            Ok(TypeInfo::new(TypeKind::Program, Vec::new(), false))
        }
        AstNode::FunctionDef(function) => {
            let mut param_types = if function.param_types.is_empty() {
                vec![TypeInfo::any(); function.params.len()]
            } else {
                function.param_types.clone()
            };
            let mut inferred_params: HashMap<String, TypeInfo> = function
                .params
                .iter()
                .cloned()
                .zip(param_types.iter().cloned())
                .collect();
            constrain_expr(&function.body, &TypeInfo::any(), &mut inferred_params, env)?;
            param_types = function
                .params
                .iter()
                .map(|name| {
                    inferred_params
                        .get(name)
                        .cloned()
                        .unwrap_or_else(TypeInfo::any)
                })
                .collect();
            let provisional_return = function.return_type.clone().unwrap_or_else(TypeInfo::any);
            env.funcs.insert(
                function.name.clone(),
                FunctionSignature {
                    param_types: param_types.clone(),
                    return_type: provisional_return.clone(),
                    scheme: None,
                },
            );
            let mut local_env = env.clone();
            for (name, param_type) in function.params.iter().zip(param_types.iter()) {
                local_env.vars.insert(name.clone(), param_type.clone());
            }
            let body_type = infer(&function.body, warnings, &mut local_env)?;
            let final_return = if let Some(return_type) = &function.return_type {
                assert_type(
                    &body_type,
                    return_type,
                    &format!("function {} return", function.name),
                )?;
                return_type.clone()
            } else {
                body_type
            };
            let resolved_param_types = param_types;
            let resolved_return_type = final_return;
            let hm_scheme = infer_function_scheme(
                &FunctionDef {
                    name: function.name.clone(),
                    params: function.params.clone(),
                    param_types: resolved_param_types.clone(),
                    return_type: Some(resolved_return_type.clone()),
                    body: function.body.clone(),
                },
                env,
            );
            env.funcs.insert(
                function.name.clone(),
                FunctionSignature {
                    param_types: resolved_param_types,
                    return_type: resolved_return_type,
                    scheme: hm_scheme,
                },
            );
            Ok(TypeInfo::new(TypeKind::Program, Vec::new(), false))
        }
        AstNode::ExportStatement(stmt) => {
            let result = infer(&stmt.statement, warnings, env)?;
            let name = match stmt.statement.as_ref() {
                AstNode::LetStatement(binding) => binding.name.clone(),
                AstNode::FunctionDef(function) => function.name.clone(),
                _ => {
                    return Err(LanguageError::new(
                        Stage::Typecheck,
                        "export may only wrap let or fn statements",
                        None,
                    ))
                }
            };
            env.exports.insert(name);
            Ok(result)
        }
        AstNode::UseStatement(stmt) => {
            let mut resolved = PathBuf::from(&stmt.path);
            if resolved.is_relative() {
                if let Some(module_dir) = &env.module_dir {
                    resolved = module_dir.join(resolved);
                }
            }
            resolved = resolved.canonicalize().map_err(|_| {
                LanguageError::new(
                    Stage::Typecheck,
                    format!("import target not found: {}", resolved.display()),
                    None,
                )
            })?;
            if env.import_stack.contains(&resolved) {
                return Err(LanguageError::new(
                    Stage::Typecheck,
                    format!("cyclic import detected for {}", resolved.display()),
                    None,
                ));
            }
            env.import_stack.insert(resolved.clone());
            let source = fs::read_to_string(&resolved).map_err(|_| {
                LanguageError::new(
                    Stage::Typecheck,
                    format!("import target not found: {}", resolved.display()),
                    None,
                )
            })?;
            let (_tokens, ast) = parse_source_via_syntax(&source)?;
            let mut imported_env = TypeEnv::new(resolved.parent().map(Path::to_path_buf));
            imported_env.import_stack = env.import_stack.clone();
            infer(&ast, warnings, &mut imported_env)?;
            let imported_names: HashSet<String> = if imported_env.exports.is_empty() {
                imported_env
                    .vars
                    .keys()
                    .cloned()
                    .chain(imported_env.funcs.keys().cloned())
                    .collect()
            } else {
                imported_env.exports.clone()
            };
            for name in imported_names {
                if let Some(value) = imported_env.vars.get(&name) {
                    env.vars.insert(name.clone(), value.clone());
                }
                if let Some(value) = imported_env.funcs.get(&name) {
                    env.funcs.insert(name.clone(), value.clone());
                }
            }
            env.import_stack.remove(&resolved);
            Ok(TypeInfo::new(TypeKind::Program, Vec::new(), false))
        }
        AstNode::Program { statements } => {
            let mut last = TypeInfo::new(TypeKind::Program, Vec::new(), false);
            for statement in statements {
                last = infer(statement, warnings, env)?;
            }
            Ok(last)
        }
    }
}

fn compose_sequence(sequence: &[u8]) -> Result<u8, LanguageError> {
    if sequence.is_empty() {
        return Err(LanguageError::new(
            Stage::Execution,
            "fractal sequence cannot be empty",
            None,
        ));
    }
    let mut iter = sequence.iter();
    let first = *iter.next().unwrap();
    let mut composed = parse_operator_index(first)?;
    for operator in iter {
        composed = composed.compose(parse_operator_index(*operator)?);
    }
    Ok(composed.index() as u8)
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct UserFunction {
    name: String,
    params: Vec<String>,
    param_types: Vec<TypeInfo>,
    return_type: TypeInfo,
    body: Vec<Instruction>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct LoadedModule {
    vars: HashMap<String, Value>,
    funcs: HashMap<String, UserFunction>,
    exports: Vec<String>,
}

#[derive(Debug, Clone)]
struct RuntimeEnv {
    vars: HashMap<String, Value>,
    funcs: HashMap<String, UserFunction>,
    module_dir: Option<PathBuf>,
    module_cache: HashMap<PathBuf, LoadedModule>,
    module_stack: HashSet<PathBuf>,
    exports: HashSet<String>,
}

impl RuntimeEnv {
    fn new(module_dir: Option<PathBuf>) -> Self {
        Self {
            vars: HashMap::new(),
            funcs: HashMap::new(),
            module_dir,
            module_cache: HashMap::new(),
            module_stack: HashSet::new(),
            exports: HashSet::new(),
        }
    }
}

fn lower(node: &AstNode, out: &mut Vec<Instruction>) {
    match node {
        AstNode::StateLiteral {
            operator,
            domain,
            drive,
        } => out.push(Instruction::PushState {
            operator: *operator,
            domain: domain.clone(),
            drive: *drive,
        }),
        AstNode::DriveLiteral { drive } => out.push(Instruction::PushDrive(*drive)),
        AstNode::FractalLiteral { sequence } => {
            out.push(Instruction::PushFractal(sequence.clone()))
        }
        AstNode::RpmCall { expr } => {
            lower(expr, out);
            out.push(Instruction::Rpm);
        }
        AstNode::Identifier { name } => out.push(Instruction::LoadVar(name.clone())),
        AstNode::StringLiteral { value } => out.push(Instruction::PushString(value.clone())),
        AstNode::CallExpr { callee, args } => {
            for arg in args {
                lower(arg, out);
            }
            out.push(Instruction::Call {
                name: callee.clone(),
                argc: args.len(),
            });
        }
        AstNode::BinaryExpr { op, left, right } => {
            lower(left, out);
            lower(right, out);
            out.push(match op {
                BinaryOp::Arrow => Instruction::Arrow,
                BinaryOp::Times => Instruction::Times,
                BinaryOp::Divide => Instruction::Divide,
                BinaryOp::Circ => Instruction::Circ,
            });
        }
        AstNode::LetStatement(stmt) => {
            lower(&stmt.expr, out);
            out.push(Instruction::StoreVar {
                name: stmt.name.clone(),
                annotation: stmt.annotation.clone(),
            });
        }
        AstNode::FunctionDef(function) => {
            let mut body = Vec::new();
            lower(&function.body, &mut body);
            out.push(Instruction::DefFunc {
                name: function.name.clone(),
                params: function.params.clone(),
                param_types: function.param_types.clone(),
                return_type: function.return_type.clone(),
                body,
            });
        }
        AstNode::UseStatement(stmt) => out.push(Instruction::Import(stmt.path.clone())),
        AstNode::ExportStatement(stmt) => {
            lower(&stmt.statement, out);
            let name = match stmt.statement.as_ref() {
                AstNode::LetStatement(binding) => binding.name.clone(),
                AstNode::FunctionDef(function) => function.name.clone(),
                _ => unreachable!(),
            };
            out.push(Instruction::ExportName(name));
        }
        AstNode::Program { statements } => {
            for (index, statement) in statements.iter().enumerate() {
                lower(statement, out);
                if index < statements.len() - 1 {
                    out.push(Instruction::EmitResult);
                }
            }
            out.push(Instruction::BuildProgramResult);
        }
    }
}

fn value_matches_type(value: &Value, expected: &TypeInfo) -> bool {
    if expected.kind == TypeKind::Any {
        return true;
    }
    match expected.kind {
        TypeKind::State => matches!(value, Value::State(_)),
        TypeKind::Drive => matches!(value, Value::Drive(_)),
        TypeKind::String => matches!(value, Value::String(_)),
        TypeKind::Fractal => matches!(value, Value::Fractal(_)),
        TypeKind::Rpm => matches!(value, Value::Rpm(_)),
        TypeKind::Relation => matches!(value, Value::Relation(_)),
        TypeKind::Program => matches!(value, Value::Program(_)),
        TypeKind::Any => true,
    }
}

fn execute(bytecode: &[Instruction], env: &mut RuntimeEnv) -> Result<Value, LanguageError> {
    let mut stack = Vec::new();
    for instruction in bytecode {
        execute_instruction(&mut stack, instruction, env)?;
    }
    if stack.len() != 1 {
        return Err(LanguageError::new(
            Stage::Execution,
            format!("vm halted with stack depth {} instead of 1", stack.len()),
            None,
        ));
    }
    Ok(stack.pop().unwrap())
}

fn execute_instruction(
    stack: &mut Vec<Value>,
    instruction: &Instruction,
    env: &mut RuntimeEnv,
) -> Result<(), LanguageError> {
    match instruction {
        Instruction::PushState {
            operator,
            domain,
            drive,
        } => {
            let _ = parse_operator_index(*operator)?;
            let _ = parse_domain_code(domain).ok_or_else(|| {
                LanguageError::new(Stage::Execution, format!("unknown domain {domain}"), None)
            })?;
            if let Some(drive) = drive {
                let _ = parse_drive_number(*drive)?;
            }
            stack.push(Value::State(StateValue {
                operator: *operator,
                domain: domain.clone(),
                drive: *drive,
            }));
        }
        Instruction::PushDrive(drive) => {
            let _ = parse_drive_number(*drive)?;
            stack.push(Value::Drive(*drive));
        }
        Instruction::PushFractal(sequence) => {
            if sequence.is_empty() {
                return Err(LanguageError::new(
                    Stage::Execution,
                    "fractal sequence cannot be empty",
                    None,
                ));
            }
            stack.push(Value::Fractal(FractalValue {
                sequence: sequence.clone(),
                composed_operator: compose_sequence(sequence)?,
                domain: "symbolic".to_string(),
            }));
        }
        Instruction::PushString(value) => stack.push(Value::String(value.clone())),
        Instruction::LoadVar(name) => stack.push(env.vars.get(name).cloned().ok_or_else(|| {
            LanguageError::new(Stage::Execution, format!("undefined variable {name}"), None)
        })?),
        Instruction::StoreVar { name, annotation } => {
            let value = stack.pop().ok_or_else(|| {
                LanguageError::new(Stage::Execution, "stack underflow on STORE_VAR", None)
            })?;
            if let Some(annotation) = annotation {
                if !value_matches_type(&value, annotation) {
                    return Err(LanguageError::new(
                        Stage::Execution,
                        format!(
                            "binding {name} violated its declared type {}",
                            format_type(annotation)
                        ),
                        None,
                    ));
                }
            }
            env.vars.insert(name.clone(), value.clone());
            stack.push(Value::Binding {
                name: name.clone(),
                value: Box::new(value),
            });
        }
        Instruction::Rpm => {
            let value = stack.pop().ok_or_else(|| {
                LanguageError::new(Stage::Execution, "stack underflow on RPM", None)
            })?;
            match value {
                Value::Drive(drive) => {
                    let chain = crate::ontology::PathwayNode::chain(parse_drive_number(drive)?)
                        .iter()
                        .map(ToString::to_string)
                        .collect::<Vec<_>>();
                    stack.push(Value::Rpm(RpmValue {
                        drive: Some(drive),
                        completeness: "1.0".to_string(),
                        chain,
                    }));
                }
                Value::State(state) => {
                    if let Some(drive) = state.drive {
                        let chain = crate::ontology::PathwayNode::chain(parse_drive_number(drive)?)
                            .iter()
                            .map(ToString::to_string)
                            .collect::<Vec<_>>();
                        stack.push(Value::Rpm(RpmValue {
                            drive: Some(drive),
                            completeness: "1.0".to_string(),
                            chain,
                        }));
                    } else {
                        stack.push(Value::Rpm(RpmValue {
                            drive: None,
                            completeness: "0.0".to_string(),
                            chain: vec![
                                "No explicit drive attached to the source state".to_string()
                            ],
                        }));
                    }
                }
                _ => {
                    return Err(LanguageError::new(
                        Stage::Execution,
                        "RPM expected a drive or state",
                        None,
                    ))
                }
            }
        }
        Instruction::Call { name, argc } => {
            let mut args = Vec::new();
            for _ in 0..*argc {
                args.push(stack.pop().ok_or_else(|| {
                    LanguageError::new(Stage::Execution, "stack underflow on CALL", None)
                })?);
            }
            args.reverse();
            match name.as_str() {
                "dominant_operator" => match args.as_slice() {
                    [Value::State(state)] => {
                        stack.push(Value::String(format!("CO-{}", state.operator)))
                    }
                    _ => {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "dominant_operator expects a state",
                            None,
                        ))
                    }
                },
                "dominant_state" => match args.as_slice() {
                    [Value::State(state)] => {
                        stack.push(Value::String(format!("{}{}", state.domain, state.operator)))
                    }
                    _ => {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "dominant_state expects a state",
                            None,
                        ))
                    }
                },
                "dominant_domain" => match args.as_slice() {
                    [Value::State(state)] => stack.push(Value::String(state.domain.clone())),
                    _ => {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "dominant_domain expects a state",
                            None,
                        ))
                    }
                },
                "compose" => match args.as_slice() {
                    [Value::State(left), Value::State(right)] => {
                        let operator = parse_operator_index(left.operator)?
                            .compose(parse_operator_index(right.operator)?)
                            .index() as u8;
                        stack.push(Value::State(StateValue {
                            operator,
                            domain: left.domain.clone(),
                            drive: left.drive.or(right.drive),
                        }));
                    }
                    _ => {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "compose expects two states",
                            None,
                        ))
                    }
                },
                "rpm_of" => {
                    if args.len() != 1 {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "rpm_of expects one argument",
                            None,
                        ));
                    }
                    let mut temp = vec![args[0].clone()];
                    execute_instruction(&mut temp, &Instruction::Rpm, env)?;
                    stack.push(temp.pop().unwrap());
                }
                "fractal" => {
                    if args.len() < 2 {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            "fractal expects at least two arguments",
                            None,
                        ));
                    }
                    let mut sequence = Vec::new();
                    let mut domain: Option<String> = None;
                    for arg in args {
                        match arg {
                            Value::State(state) => {
                                sequence.push(state.operator);
                                if domain.is_none() {
                                    domain = Some(state.domain);
                                }
                            }
                            Value::Fractal(fractal) => {
                                sequence.extend(fractal.sequence);
                                if domain.is_none() && fractal.domain != "symbolic" {
                                    domain = Some(fractal.domain);
                                }
                            }
                            _ => {
                                return Err(LanguageError::new(
                                    Stage::Execution,
                                    "fractal expects state or fractal arguments",
                                    None,
                                ))
                            }
                        }
                    }
                    stack.push(Value::Fractal(FractalValue {
                        composed_operator: compose_sequence(&sequence)?,
                        sequence,
                        domain: domain.unwrap_or_else(|| "symbolic".to_string()),
                    }));
                }
                _ => {
                    let function = env.funcs.get(name).cloned().ok_or_else(|| {
                        LanguageError::new(
                            Stage::Execution,
                            format!("undefined function {name}"),
                            None,
                        )
                    })?;
                    if function.params.len() != args.len() {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            format!(
                                "function {name} expects {} arguments, got {}",
                                function.params.len(),
                                args.len()
                            ),
                            None,
                        ));
                    }
                    for ((param, expected), arg) in function
                        .params
                        .iter()
                        .zip(function.param_types.iter())
                        .zip(args.iter())
                    {
                        if !value_matches_type(arg, expected) {
                            return Err(LanguageError::new(
                                Stage::Execution,
                                format!(
                                    "function {name} argument {param} violated type {}",
                                    format_type(expected)
                                ),
                                None,
                            ));
                        }
                    }
                    let mut child = env.clone();
                    for (param, arg) in function.params.iter().zip(args.into_iter()) {
                        child.vars.insert(param.clone(), arg);
                    }
                    let result = execute(&function.body, &mut child)?;
                    if !value_matches_type(&result, &function.return_type) {
                        return Err(LanguageError::new(
                            Stage::Execution,
                            format!(
                                "function {name} returned a value incompatible with {}",
                                format_type(&function.return_type)
                            ),
                            None,
                        ));
                    }
                    stack.push(result);
                }
            }
        }
        Instruction::Arrow | Instruction::Times | Instruction::Divide | Instruction::Circ => {
            execute_binary(stack, instruction)?
        }
        Instruction::DefFunc {
            name,
            params,
            param_types,
            return_type,
            body,
        } => {
            let function = UserFunction {
                name: name.clone(),
                params: params.clone(),
                param_types: if param_types.is_empty() {
                    vec![TypeInfo::any(); params.len()]
                } else {
                    param_types.clone()
                },
                return_type: return_type.clone().unwrap_or_else(TypeInfo::any),
                body: body.clone(),
            };
            env.funcs.insert(name.clone(), function.clone());
            stack.push(Value::Function(FunctionValue {
                name: name.clone(),
                params: params.clone(),
                param_types: function.param_types.clone(),
                return_type: function.return_type.clone(),
            }));
        }
        Instruction::Import(path) => execute_import(stack, env, path)?,
        Instruction::ExportName(name) => {
            env.exports.insert(name.clone());
        }
        Instruction::EmitResult => {
            let value = stack.pop().ok_or_else(|| {
                LanguageError::new(Stage::Execution, "stack underflow on EMIT_RESULT", None)
            })?;
            let mut results = match stack.pop() {
                Some(Value::Program(results)) => results,
                Some(other) => vec![other],
                None => Vec::new(),
            };
            results.push(value);
            stack.push(Value::Program(results));
        }
        Instruction::BuildProgramResult => {
            let value = stack.pop().ok_or_else(|| {
                LanguageError::new(
                    Stage::Execution,
                    "stack underflow on BUILD_PROGRAM_RESULT",
                    None,
                )
            })?;
            let mut results = match stack.pop() {
                Some(Value::Program(results)) => results,
                Some(other) => vec![other],
                None => Vec::new(),
            };
            results.push(value);
            stack.push(Value::Program(results));
        }
    }
    Ok(())
}

fn execute_binary(stack: &mut Vec<Value>, instruction: &Instruction) -> Result<(), LanguageError> {
    let right = stack.pop().ok_or_else(|| {
        LanguageError::new(Stage::Execution, "stack underflow on binary operator", None)
    })?;
    let left = stack.pop().ok_or_else(|| {
        LanguageError::new(Stage::Execution, "stack underflow on binary operator", None)
    })?;
    match instruction {
        Instruction::Times => match (left, right) {
            (Value::State(left), Value::State(right)) => {
                let operator = parse_operator_index(left.operator)?
                    .compose(parse_operator_index(right.operator)?)
                    .index() as u8;
                stack.push(Value::State(StateValue {
                    operator,
                    domain: left.domain,
                    drive: left.drive.or(right.drive),
                }));
                Ok(())
            }
            _ => Err(LanguageError::new(
                Stage::Execution,
                "TIMES expects state operands",
                None,
            )),
        },
        Instruction::Divide => match (left, right) {
            (Value::State(left), Value::State(right)) => {
                let operator = (10 + left.operator as i16 - right.operator as i16) % 10;
                stack.push(Value::State(StateValue {
                    operator: operator as u8,
                    domain: left.domain,
                    drive: left.drive.or(right.drive),
                }));
                Ok(())
            }
            _ => Err(LanguageError::new(
                Stage::Execution,
                "DIVIDE expects state operands",
                None,
            )),
        },
        Instruction::Circ => match (left, right) {
            (Value::State(left), Value::State(right)) => {
                let sequence = vec![left.operator, right.operator];
                stack.push(Value::Fractal(FractalValue {
                    composed_operator: compose_sequence(&sequence)?,
                    sequence,
                    domain: left.domain,
                }));
                Ok(())
            }
            (Value::Fractal(left), Value::State(right)) => {
                let mut sequence = left.sequence;
                sequence.push(right.operator);
                let domain = if left.domain == "symbolic" {
                    right.domain
                } else {
                    left.domain
                };
                stack.push(Value::Fractal(FractalValue {
                    composed_operator: compose_sequence(&sequence)?,
                    sequence,
                    domain,
                }));
                Ok(())
            }
            (Value::State(left), Value::Fractal(right)) => {
                let mut sequence = vec![left.operator];
                sequence.extend(right.sequence);
                let domain = if right.domain == "symbolic" {
                    left.domain
                } else {
                    right.domain
                };
                stack.push(Value::Fractal(FractalValue {
                    composed_operator: compose_sequence(&sequence)?,
                    sequence,
                    domain,
                }));
                Ok(())
            }
            (Value::Fractal(left), Value::Fractal(right)) => {
                let mut sequence = left.sequence;
                sequence.extend(right.sequence);
                let domain = if left.domain != "symbolic" {
                    left.domain
                } else {
                    right.domain
                };
                stack.push(Value::Fractal(FractalValue {
                    composed_operator: compose_sequence(&sequence)?,
                    sequence,
                    domain,
                }));
                Ok(())
            }
            _ => Err(LanguageError::new(
                Stage::Execution,
                "CIRC expects state or fractal operands",
                None,
            )),
        },
        Instruction::Arrow => match (left, right) {
            (Value::State(left), Value::State(right)) => {
                let source_domain = parse_domain_code(&left.domain).unwrap();
                let target_domain = parse_domain_code(&right.domain).unwrap();
                let source = crate::ontology::CognitiveStateId::new(
                    parse_operator_index(left.operator)?,
                    source_domain,
                );
                let target = crate::ontology::CognitiveStateId::new(
                    parse_operator_index(right.operator)?,
                    target_domain,
                );
                let admissible =
                    parse_operator_index(right.operator)?.is_admissible(source, target);
                let domain_descent_ok = source_domain.index() <= target_domain.index();
                stack.push(Value::Relation(RelationValue {
                    relation: "dependency",
                    source: left,
                    target: right,
                    admissible,
                    domain_descent_ok,
                }));
                Ok(())
            }
            _ => Err(LanguageError::new(
                Stage::Execution,
                "ARROW expects state operands",
                None,
            )),
        },
        _ => unreachable!(),
    }
}

fn execute_import(
    stack: &mut Vec<Value>,
    env: &mut RuntimeEnv,
    path: &str,
) -> Result<(), LanguageError> {
    let mut resolved = PathBuf::from(path);
    if resolved.is_relative() {
        if let Some(module_dir) = &env.module_dir {
            resolved = module_dir.join(resolved);
        }
    }
    resolved = resolved.canonicalize().map_err(|_| {
        LanguageError::new(
            Stage::Execution,
            format!("import target not found: {}", resolved.display()),
            None,
        )
    })?;
    if env.module_stack.contains(&resolved) {
        return Err(LanguageError::new(
            Stage::Execution,
            format!("cyclic import detected for {}", resolved.display()),
            None,
        ));
    }
    if let Some(loaded) = env.module_cache.get(&resolved).cloned() {
        for export in &loaded.exports {
            if let Some(value) = loaded.vars.get(export) {
                env.vars.insert(export.clone(), value.clone());
            }
            if let Some(value) = loaded.funcs.get(export) {
                env.funcs.insert(export.clone(), value.clone());
            }
        }
        stack.push(Value::Module(ModuleValue {
            path: resolved.display().to_string(),
            exports: loaded.exports,
        }));
        return Ok(());
    }
    env.module_stack.insert(resolved.clone());
    let source = fs::read_to_string(&resolved).map_err(|_| {
        LanguageError::new(
            Stage::Execution,
            format!("import target not found: {}", resolved.display()),
            None,
        )
    })?;
    let (_tokens, ast) = parse_source_via_syntax(&source)?;
    let mut warnings = Vec::new();
    let mut type_env = TypeEnv::new(resolved.parent().map(Path::to_path_buf));
    infer(&ast, &mut warnings, &mut type_env)?;
    let mut bytecode = Vec::new();
    lower(&ast, &mut bytecode);
    let mut child = RuntimeEnv::new(resolved.parent().map(Path::to_path_buf));
    let _ = execute(&bytecode, &mut child)?;
    let exports: Vec<String> = if child.exports.is_empty() {
        child
            .vars
            .keys()
            .cloned()
            .chain(child.funcs.keys().cloned())
            .collect()
    } else {
        child.exports.iter().cloned().collect()
    };
    let mut vars = HashMap::new();
    let mut funcs = HashMap::new();
    for export in &exports {
        if let Some(value) = child.vars.get(export) {
            env.vars.insert(export.clone(), value.clone());
            vars.insert(export.clone(), value.clone());
        }
        if let Some(value) = child.funcs.get(export) {
            env.funcs.insert(export.clone(), value.clone());
            funcs.insert(export.clone(), value.clone());
        }
    }
    env.module_cache.insert(
        resolved.clone(),
        LoadedModule {
            vars,
            funcs,
            exports: exports.clone(),
        },
    );
    env.module_stack.remove(&resolved);
    stack.push(Value::Module(ModuleValue {
        path: resolved.display().to_string(),
        exports,
    }));
    Ok(())
}

fn compile_source(source: &str, module_dir: Option<PathBuf>) -> CompilationArtifact {
    match parse_source_via_syntax(source) {
        Ok((tokens, ast)) => {
            let mut warnings = Vec::new();
            let mut type_env = TypeEnv::new(module_dir.clone());
            match infer(&ast, &mut warnings, &mut type_env) {
                Ok(type_info) => {
                    let mut bytecode = Vec::new();
                    lower(&ast, &mut bytecode);
                    let mut runtime = RuntimeEnv::new(module_dir);
                    match execute(&bytecode, &mut runtime) {
                        Ok(result) => CompilationArtifact {
                            source: source.to_string(),
                            tokens: tokens
                                .into_iter()
                                .filter(|token| token.kind != TokenKind::Eof)
                                .collect(),
                            ast: Some(ast),
                            type_info: Some(type_info),
                            bytecode,
                            result: Some(result),
                            warnings,
                            valid: true,
                            error: None,
                        },
                        Err(error) => invalid_artifact(source, tokens, error),
                    }
                }
                Err(error) => invalid_artifact(source, tokens, error),
            }
        }
        Err(error) => invalid_artifact(source, Vec::new(), error),
    }
}

fn invalid_artifact(
    source: &str,
    tokens: Vec<LexToken>,
    error: LanguageError,
) -> CompilationArtifact {
    CompilationArtifact {
        source: source.to_string(),
        tokens: tokens
            .into_iter()
            .filter(|token| token.kind != TokenKind::Eof)
            .collect(),
        ast: None,
        type_info: None,
        bytecode: Vec::new(),
        result: None,
        warnings: Vec::new(),
        valid: false,
        error: Some(error.to_string()),
    }
}

pub fn compile_expression(source: &str) -> CompilationArtifact {
    compile_source(source, None)
}

pub fn compile_file(path: impl AsRef<Path>) -> CompilationArtifact {
    let path = path.as_ref();
    match fs::read_to_string(path) {
        Ok(source) => compile_source(&source, path.parent().map(Path::to_path_buf)),
        Err(error) => CompilationArtifact {
            source: String::new(),
            tokens: Vec::new(),
            ast: None,
            type_info: None,
            bytecode: Vec::new(),
            result: None,
            warnings: Vec::new(),
            valid: false,
            error: Some(format!(
                "execution: failed to read {}: {error}",
                path.display()
            )),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn tmp_dir() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("casc_{suffix}"));
        fs::create_dir_all(&path).unwrap();
        path
    }

    #[test]
    fn typed_function_executes() {
        let artifact = compile_expression(
            "fn bridge(x: state[C], y: state[E]): relation = x -> y; bridge(C2, E5)",
        );
        assert!(artifact.valid, "{:?}", artifact.error);
    }

    #[test]
    fn typed_binding_rejects_wrong_type() {
        let artifact = compile_expression("let label: state[C] = \"hello\"; label");
        assert!(!artifact.valid);
        assert!(artifact.error.unwrap().contains("binding label"));
    }

    #[test]
    fn export_limits_imported_surface() {
        let dir = tmp_dir();
        let helper = dir.join("helper.cas");
        let main = dir.join("main.cas");
        fs::write(&helper, "export let base: state[C] = CO-2^C_{F2}; fn hidden(x: state[C]): relation = x -> CO-5^E_{F4}").unwrap();
        fs::write(&main, format!("use \"{}\"; hidden(base)", helper.display())).unwrap();
        let artifact = compile_file(&main);
        assert!(!artifact.valid);
        assert!(artifact
            .error
            .unwrap()
            .contains("undefined function hidden"));
    }

    #[test]
    fn showcase_program_executes() {
        let artifact = compile_file("../docs/CAS_SHOWCASE_APP.cas");
        assert!(artifact.valid, "{:?}", artifact.error);
        let json = artifact.to_json();
        assert_eq!(json["result"]["kind"], "program");
        assert_eq!(json["result"]["final_result"]["kind"], "relation");
    }

    #[test]
    fn phi_literal_executes() {
        let artifact = compile_expression("let motif: fractal = Phi<2:4:8>; motif");
        assert!(artifact.valid, "{:?}", artifact.error);
        let json = artifact.to_json();
        assert_eq!(json["result"]["final_result"]["kind"], "fractal");
        assert_eq!(
            json["result"]["final_result"]["sequence"],
            serde_json::json!([2, 4, 8])
        );
    }

    #[test]
    fn unannotated_arrow_function_inferrs_state_params() {
        let artifact = compile_expression("fn bridge(x, y) = x -> y; bridge(C2, E5)");
        assert!(artifact.valid, "{:?}", artifact.error);
        assert!(artifact.warnings.is_empty(), "{:?}", artifact.warnings);
        assert_eq!(artifact.to_json()["type"]["kind"], "relation");
    }

    #[test]
    fn builtin_usage_inferrs_state_param() {
        let artifact = compile_expression("fn show(x) = dominant_operator(x); show(C2)");
        assert!(artifact.valid, "{:?}", artifact.error);
        assert!(artifact.warnings.is_empty(), "{:?}", artifact.warnings);
        assert_eq!(artifact.to_json()["type"]["kind"], "string");
    }

    #[test]
    fn identity_function_infers_state_return_at_callsite() {
        let artifact = compile_expression("fn id(x) = x; id(C2)");
        assert!(artifact.valid, "{:?}", artifact.error);
        assert_eq!(artifact.to_json()["type"]["kind"], "state");
    }

    #[test]
    fn identity_function_infers_string_return_at_callsite() {
        let artifact = compile_expression("fn id(x) = x; id(\"hello\")");
        assert!(artifact.valid, "{:?}", artifact.error);
        assert_eq!(artifact.to_json()["type"]["kind"], "string");
    }
}
