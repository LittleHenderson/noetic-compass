use std::fs;
use std::path::Path;

use serde::Serialize;
use thiserror::Error;

pub const CAS_GRAMMAR_BNF: &str = r#"<program>          ::= <statement> (";" <statement>)* ;
<statement>        ::= <export_stmt> | <let_stmt> | <fn_stmt> | <use_stmt> | <expression> ;
<export_stmt>      ::= "export" (<let_stmt> | <fn_stmt>) ;
<let_stmt>         ::= "let" <ident> (":" <type_expr>)? "=" <expression> ;
<fn_stmt>          ::= "fn" <ident> "(" <typed_param_list>? ")" (":" <type_expr>)? "=" <expression> ;
<use_stmt>         ::= "use" <string> ;
<typed_param_list> ::= <typed_param> ("," <typed_param>)* ;
<typed_param>      ::= <ident> (":" <type_expr>)? ;
<type_expr>        ::= <type_name> ("[" <domain_list> "]")? ;
<type_name>        ::= "state" | "drive" | "string" | "fractal" | "rpm" | "relation" | "program" | "number" | "meta_set" | "meta_symbol" | "meta_assertion" | "any" ;
<domain_list>      ::= <domain> ("," <domain>)* ;
<expression>       ::= <meta_relation> ;
<meta_relation>    ::= <relation> (("∈" | "∉" | "⊂" | "⊆" | "⊃" | "⊇") <relation>)* ;
<relation>         ::= <composition> (("->") <composition>)* ;
<composition>      ::= <primary> (("*" | "/" | "circ") <primary>)* ;
<primary>          ::= <state> | <state_ref> | <drive_ref> | <rpm_call> | <phi_literal> | <cardinality> | <meta_set> | <meta_symbol> | "∅" | <number> | <call> | <ident> | <string> | "(" <expression> ")" ;
<cardinality>      ::= "|" <meta_set> "|" ;
<meta_set>         ::= "Noetics" | "Domains" | "Worlds" | "Drives" | "Registers" | "States" | "Foundations" | "SubFoundations" | "Foundation_1" | ... | "Foundation_7" ;
<meta_symbol>      ::= <domain> | "T" | "A" | "f" | "E" ;
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
    pub fn new(stage: Stage, message: impl Into<String>, position: Option<usize>) -> Self {
        Self {
            stage: stage.as_str(),
            position: position.map(|p| format!("@{p}")).unwrap_or_default(),
            message: message.into(),
        }
    }

    pub fn stage_label(&self) -> &'static str {
        self.stage
    }

    pub fn message(&self) -> &str {
        &self.message
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum TokenKind {
    Export,
    Let,
    Fn,
    Use,
    Co,
    StateRef,
    Domain,
    Drive,
    Rpm,
    Phi,
    Ident,
    String,
    Number,
    Arrow,
    Member,
    NotMember,
    Subset,
    SubsetEq,
    Superset,
    SupersetEq,
    EmptySet,
    Times,
    Divide,
    Circ,
    Caret,
    Underscore,
    LBrace,
    RBrace,
    LParen,
    RParen,
    LBracket,
    RBracket,
    LAngle,
    RAngle,
    Pipe,
    Colon,
    Comma,
    Equals,
    Semi,
    Eof,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LexToken {
    pub kind: TokenKind,
    pub value: String,
    pub position: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TypeKind {
    Any,
    State,
    Drive,
    String,
    Fractal,
    Rpm,
    Relation,
    Program,
    Number,
    MetaSet,
    MetaSymbol,
    MetaAssertion,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct TypeInfo {
    pub kind: TypeKind,
    pub domains: Vec<String>,
    pub singular: bool,
}

impl TypeInfo {
    pub fn new(kind: TypeKind, domains: Vec<String>, singular: bool) -> Self {
        Self {
            kind,
            domains,
            singular,
        }
    }

    pub fn any() -> Self {
        Self::new(TypeKind::Any, Vec::new(), false)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LetStatement {
    pub name: String,
    pub annotation: Option<TypeInfo>,
    pub expr: Box<AstNode>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FunctionDef {
    pub name: String,
    pub params: Vec<String>,
    pub param_types: Vec<TypeInfo>,
    pub return_type: Option<TypeInfo>,
    pub body: Box<AstNode>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct UseStatement {
    pub path: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ExportStatement {
    pub statement: Box<AstNode>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum BinaryOp {
    Arrow,
    Times,
    Divide,
    Circ,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum MetaOp {
    Member,
    NotMember,
    Subset,
    SubsetEq,
    Superset,
    SupersetEq,
    Equals,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "node")]
pub enum AstNode {
    StateLiteral {
        operator: u8,
        domain: String,
        drive: Option<u8>,
        domain_explicit: bool,
    },
    DriveLiteral {
        drive: u8,
    },
    FractalLiteral {
        sequence: Vec<u8>,
    },
    RpmCall {
        expr: Box<AstNode>,
    },
    Identifier {
        name: String,
    },
    StringLiteral {
        value: String,
    },
    NumberLiteral {
        value: i64,
    },
    MetaSetLiteral {
        name: String,
    },
    MetaSymbol {
        name: String,
        symbol_kind: String,
    },
    EmptySetLiteral,
    CardinalityExpr {
        collection: Box<AstNode>,
    },
    MetaAssertion {
        op: MetaOp,
        left: Box<AstNode>,
        right: Box<AstNode>,
    },
    CallExpr {
        callee: String,
        args: Vec<AstNode>,
    },
    BinaryExpr {
        op: BinaryOp,
        left: Box<AstNode>,
        right: Box<AstNode>,
    },
    LetStatement(LetStatement),
    FunctionDef(FunctionDef),
    UseStatement(UseStatement),
    ExportStatement(ExportStatement),
    Program {
        statements: Vec<AstNode>,
    },
}

fn decode_string_literal(raw: &str) -> String {
    let body = &raw[1..raw.len() - 1];
    body.replace("\\\"", "\"")
        .replace("\\\\", "\\")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
}

fn decode_path_literal(raw: &str) -> String {
    raw[1..raw.len() - 1]
        .replace("\\\"", "\"")
        .replace("\\\\", "\\")
}

fn type_keyword_to_kind(name: &str) -> Result<TypeKind, LanguageError> {
    match name {
        "any" => Ok(TypeKind::Any),
        "state" => Ok(TypeKind::State),
        "drive" => Ok(TypeKind::Drive),
        "string" => Ok(TypeKind::String),
        "fractal" => Ok(TypeKind::Fractal),
        "rpm" => Ok(TypeKind::Rpm),
        "relation" => Ok(TypeKind::Relation),
        "program" => Ok(TypeKind::Program),
        "number" => Ok(TypeKind::Number),
        "meta_set" => Ok(TypeKind::MetaSet),
        "meta_symbol" => Ok(TypeKind::MetaSymbol),
        "meta_assertion" => Ok(TypeKind::MetaAssertion),
        _ => Err(LanguageError::new(
            Stage::Parsing,
            format!("unknown type {name}"),
            None,
        )),
    }
}

fn canonical_meta_set_name(name: &str) -> Option<&'static str> {
    match name {
        "Noetics" => Some("Noetics"),
        "Domains" | "Worlds" => Some("Domains"),
        "Drives" => Some("Drives"),
        "Registers" => Some("Registers"),
        "States" => Some("States"),
        "Foundations" => Some("Foundations"),
        "SubFoundations" | "DriveRegisterPositions" | "SubFoundationPositions" => {
            Some("SubFoundations")
        }
        "Foundation_1" => Some("Foundation_1"),
        "Foundation_2" => Some("Foundation_2"),
        "Foundation_3" => Some("Foundation_3"),
        "Foundation_4" => Some("Foundation_4"),
        "Foundation_5" => Some("Foundation_5"),
        "Foundation_6" => Some("Foundation_6"),
        "Foundation_7" => Some("Foundation_7"),
        "EmptySet" => Some("EmptySet"),
        _ => None,
    }
}

fn parse_drive_token_value(value: &str) -> Result<u8, LanguageError> {
    let body = value.strip_prefix("F_").or_else(|| value.strip_prefix('F'));
    body.and_then(|digits| digits.parse::<u8>().ok())
        .ok_or_else(|| LanguageError::new(Stage::Parsing, format!("invalid drive {value}"), None))
}

pub fn lex(source: &str) -> Result<Vec<LexToken>, LanguageError> {
    let mut tokens = Vec::new();
    let mut index = 0usize;
    while index < source.len() {
        let rest = &source[index..];
        let ch = rest.chars().next().unwrap();
        if ch == ' ' || ch == '\t' || ch == '\r' {
            index += ch.len_utf8();
            continue;
        }
        if ch == '\n' {
            tokens.push(LexToken {
                kind: TokenKind::Semi,
                value: "\n".to_string(),
                position: index,
            });
            index += 1;
            continue;
        }
        if ch == '#' || rest.starts_with("//") {
            while index < source.len() && !source[index..].starts_with('\n') {
                index += source[index..].chars().next().unwrap().len_utf8();
            }
            continue;
        }
        if rest.starts_with("->") {
            tokens.push(LexToken {
                kind: TokenKind::Arrow,
                value: "->".to_string(),
                position: index,
            });
            index += 2;
            continue;
        }
        if ch == '\u{2209}' {
            tokens.push(LexToken {
                kind: TokenKind::NotMember,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2208}' {
            tokens.push(LexToken {
                kind: TokenKind::Member,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2286}' {
            tokens.push(LexToken {
                kind: TokenKind::SubsetEq,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2282}' {
            tokens.push(LexToken {
                kind: TokenKind::Subset,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2287}' {
            tokens.push(LexToken {
                kind: TokenKind::SupersetEq,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2283}' {
            tokens.push(LexToken {
                kind: TokenKind::Superset,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch == '\u{2205}' {
            tokens.push(LexToken {
                kind: TokenKind::EmptySet,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if rest.starts_with("CO-") {
            let start = index;
            index += 3;
            while index < source.len() && source[index..].chars().next().unwrap().is_ascii_digit() {
                index += 1;
            }
            tokens.push(LexToken {
                kind: TokenKind::Co,
                value: source[start..index].to_string(),
                position: start,
            });
            continue;
        }
        if rest.starts_with("Phi")
            && rest[3..]
                .chars()
                .next()
                .map(|ch| !ch.is_ascii_alphanumeric() && ch != '_')
                .unwrap_or(true)
        {
            tokens.push(LexToken {
                kind: TokenKind::Phi,
                value: "Phi".to_string(),
                position: index,
            });
            index += 3;
            continue;
        }
        if matches!(ch, 'P' | 'C' | 'E' | 'O') {
            let start = index;
            index += 1;
            while index < source.len() && source[index..].chars().next().unwrap().is_ascii_digit() {
                index += 1;
            }
            if index > start + 1 {
                tokens.push(LexToken {
                    kind: TokenKind::StateRef,
                    value: source[start..index].to_string(),
                    position: start,
                });
            } else {
                tokens.push(LexToken {
                    kind: TokenKind::Domain,
                    value: source[start..index].to_string(),
                    position: start,
                });
            }
            continue;
        }
        if ch == 'F'
            && source[index + ch.len_utf8()..]
                .chars()
                .next()
                .map(|next| next.is_ascii_digit() || next == '_')
                .unwrap_or(false)
        {
            let start = index;
            index += 1;
            if source[index..].starts_with('_') {
                index += 1;
            }
            while index < source.len() && source[index..].chars().next().unwrap().is_ascii_digit() {
                index += 1;
            }
            tokens.push(LexToken {
                kind: TokenKind::Drive,
                value: source[start..index].to_string(),
                position: start,
            });
            continue;
        }
        if ch == '"' {
            let start = index;
            index += 1;
            let mut escaped = false;
            while index < source.len() {
                let next = source[index..].chars().next().unwrap();
                index += next.len_utf8();
                if escaped {
                    escaped = false;
                    continue;
                }
                if next == '\\' {
                    escaped = true;
                } else if next == '"' {
                    break;
                }
            }
            if !source[start..index].ends_with('"') {
                return Err(LanguageError::new(
                    Stage::Lexing,
                    "unterminated string literal",
                    Some(start),
                ));
            }
            tokens.push(LexToken {
                kind: TokenKind::String,
                value: source[start..index].to_string(),
                position: start,
            });
            continue;
        }
        if ch == '_' {
            tokens.push(LexToken {
                kind: TokenKind::Underscore,
                value: "_".to_string(),
                position: index,
            });
            index += 1;
            continue;
        }
        if ch == '\u{03A6}' {
            tokens.push(LexToken {
                kind: TokenKind::Phi,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        if ch.is_ascii_alphabetic() {
            let start = index;
            index += 1;
            while index < source.len() {
                let next = source[index..].chars().next().unwrap();
                if next.is_ascii_alphanumeric() || next == '_' {
                    index += 1;
                } else {
                    break;
                }
            }
            let value = &source[start..index];
            let kind = match value {
                "export" => TokenKind::Export,
                "let" => TokenKind::Let,
                "fn" => TokenKind::Fn,
                "use" => TokenKind::Use,
                "RPM" => TokenKind::Rpm,
                "Phi" => TokenKind::Phi,
                "circ" => TokenKind::Circ,
                _ => TokenKind::Ident,
            };
            tokens.push(LexToken {
                kind,
                value: value.to_string(),
                position: start,
            });
            continue;
        }
        if ch.is_ascii_digit() {
            let start = index;
            index += 1;
            while index < source.len() && source[index..].chars().next().unwrap().is_ascii_digit() {
                index += 1;
            }
            tokens.push(LexToken {
                kind: TokenKind::Number,
                value: source[start..index].to_string(),
                position: start,
            });
            continue;
        }
        let kind = match ch {
            '*' | '\u{00d7}' => Some(TokenKind::Times),
            '/' | '\u{00f7}' => Some(TokenKind::Divide),
            '\u{2218}' => Some(TokenKind::Circ),
            '^' => Some(TokenKind::Caret),
            '{' => Some(TokenKind::LBrace),
            '}' => Some(TokenKind::RBrace),
            '(' => Some(TokenKind::LParen),
            ')' => Some(TokenKind::RParen),
            '[' => Some(TokenKind::LBracket),
            ']' => Some(TokenKind::RBracket),
            '<' | '\u{27e8}' => Some(TokenKind::LAngle),
            '>' | '\u{27e9}' => Some(TokenKind::RAngle),
            ':' => Some(TokenKind::Colon),
            ',' => Some(TokenKind::Comma),
            '=' => Some(TokenKind::Equals),
            '|' => Some(TokenKind::Pipe),
            ';' => Some(TokenKind::Semi),
            _ => None,
        };
        if let Some(kind) = kind {
            tokens.push(LexToken {
                kind,
                value: ch.to_string(),
                position: index,
            });
            index += ch.len_utf8();
            continue;
        }
        return Err(LanguageError::new(
            Stage::Lexing,
            format!("unexpected character {ch:?}"),
            Some(index),
        ));
    }
    tokens.push(LexToken {
        kind: TokenKind::Eof,
        value: String::new(),
        position: source.len(),
    });
    Ok(tokens)
}

struct Parser {
    tokens: Vec<LexToken>,
    index: usize,
}

impl Parser {
    fn new(tokens: Vec<LexToken>) -> Self {
        Self { tokens, index: 0 }
    }

    fn current(&self) -> &LexToken {
        &self.tokens[self.index]
    }

    fn advance(&mut self) -> LexToken {
        let token = self.current().clone();
        self.index += 1;
        token
    }

    fn expect(&mut self, kind: TokenKind) -> Result<LexToken, LanguageError> {
        let token = self.current().clone();
        if token.kind != kind {
            return Err(LanguageError::new(
                Stage::Parsing,
                format!("expected {:?}, got {:?}", kind, token.kind),
                Some(token.position),
            ));
        }
        Ok(self.advance())
    }

    fn parse(mut self) -> Result<AstNode, LanguageError> {
        let mut statements = Vec::new();
        while self.current().kind == TokenKind::Semi {
            self.advance();
        }
        while self.current().kind != TokenKind::Eof {
            statements.push(self.parse_statement()?);
            while self.current().kind == TokenKind::Semi {
                self.advance();
            }
        }
        if statements.is_empty() {
            return Err(LanguageError::new(Stage::Parsing, "empty program", None));
        }
        if statements.len() == 1 {
            Ok(statements.remove(0))
        } else {
            Ok(AstNode::Program { statements })
        }
    }

    fn parse_statement(&mut self) -> Result<AstNode, LanguageError> {
        match self.current().kind {
            TokenKind::Export => {
                let token = self.advance();
                let inner = self.parse_statement()?;
                match inner {
                    AstNode::LetStatement(_) | AstNode::FunctionDef(_) => {
                        Ok(AstNode::ExportStatement(ExportStatement {
                            statement: Box::new(inner),
                        }))
                    }
                    _ => Err(LanguageError::new(
                        Stage::Parsing,
                        "export may only be applied to let or fn statements",
                        Some(token.position),
                    )),
                }
            }
            TokenKind::Let => {
                self.advance();
                let name = self.expect(TokenKind::Ident)?.value;
                let annotation = if self.current().kind == TokenKind::Colon {
                    self.advance();
                    Some(self.parse_type()?)
                } else {
                    None
                };
                self.expect(TokenKind::Equals)?;
                Ok(AstNode::LetStatement(LetStatement {
                    name,
                    annotation,
                    expr: Box::new(self.parse_expression()?),
                }))
            }
            TokenKind::Fn => {
                self.advance();
                let name = self.expect(TokenKind::Ident)?.value;
                self.expect(TokenKind::LParen)?;
                let mut params = Vec::new();
                let mut param_types = Vec::new();
                if self.current().kind != TokenKind::RParen {
                    loop {
                        params.push(self.expect(TokenKind::Ident)?.value);
                        if self.current().kind == TokenKind::Colon {
                            self.advance();
                            param_types.push(self.parse_type()?);
                        } else {
                            param_types.push(TypeInfo::any());
                        }
                        if self.current().kind != TokenKind::Comma {
                            break;
                        }
                        self.advance();
                    }
                }
                self.expect(TokenKind::RParen)?;
                let return_type = if self.current().kind == TokenKind::Colon {
                    self.advance();
                    Some(self.parse_type()?)
                } else {
                    None
                };
                self.expect(TokenKind::Equals)?;
                Ok(AstNode::FunctionDef(FunctionDef {
                    name,
                    params,
                    param_types,
                    return_type,
                    body: Box::new(self.parse_expression()?),
                }))
            }
            TokenKind::Use => {
                self.advance();
                let path = decode_path_literal(&self.expect(TokenKind::String)?.value);
                Ok(AstNode::UseStatement(UseStatement { path }))
            }
            _ => self.parse_expression(),
        }
    }

    fn parse_type(&mut self) -> Result<TypeInfo, LanguageError> {
        let kind = type_keyword_to_kind(&self.expect(TokenKind::Ident)?.value)?;
        let mut domains = Vec::new();
        if self.current().kind == TokenKind::LBracket {
            self.advance();
            domains.push(self.expect(TokenKind::Domain)?.value);
            while self.current().kind == TokenKind::Comma {
                self.advance();
                domains.push(self.expect(TokenKind::Domain)?.value);
            }
            self.expect(TokenKind::RBracket)?;
        }
        let singular = matches!(
            kind,
            TypeKind::State
                | TypeKind::Drive
                | TypeKind::String
                | TypeKind::Fractal
                | TypeKind::Rpm
                | TypeKind::Number
                | TypeKind::MetaSet
                | TypeKind::MetaSymbol
                | TypeKind::MetaAssertion
        );
        Ok(TypeInfo::new(kind, domains, singular))
    }

    fn parse_expression(&mut self) -> Result<AstNode, LanguageError> {
        let mut expr = self.parse_relation()?;
        while matches!(
            self.current().kind,
            TokenKind::Member
                | TokenKind::NotMember
                | TokenKind::Subset
                | TokenKind::SubsetEq
                | TokenKind::Superset
                | TokenKind::SupersetEq
        ) {
            let token = self.advance();
            let rhs = self.parse_relation()?;
            let op = match token.kind {
                TokenKind::Member => MetaOp::Member,
                TokenKind::NotMember => MetaOp::NotMember,
                TokenKind::Subset => MetaOp::Subset,
                TokenKind::SubsetEq => MetaOp::SubsetEq,
                TokenKind::Superset => MetaOp::Superset,
                TokenKind::SupersetEq => MetaOp::SupersetEq,
                _ => unreachable!(),
            };
            expr = AstNode::MetaAssertion {
                op,
                left: Box::new(expr),
                right: Box::new(rhs),
            };
        }
        if self.current().kind == TokenKind::Equals
            && matches!(expr, AstNode::CardinalityExpr { .. })
        {
            self.advance();
            let rhs = self.parse_expression()?;
            expr = AstNode::MetaAssertion {
                op: MetaOp::Equals,
                left: Box::new(expr),
                right: Box::new(rhs),
            };
        }
        Ok(expr)
    }

    fn parse_relation(&mut self) -> Result<AstNode, LanguageError> {
        let mut expr = self.parse_composition()?;
        while self.current().kind == TokenKind::Arrow {
            self.advance();
            let rhs = self.parse_composition()?;
            expr = AstNode::BinaryExpr {
                op: BinaryOp::Arrow,
                left: Box::new(expr),
                right: Box::new(rhs),
            };
        }
        Ok(expr)
    }

    fn parse_composition(&mut self) -> Result<AstNode, LanguageError> {
        let mut expr = self.parse_primary()?;
        while matches!(
            self.current().kind,
            TokenKind::Times | TokenKind::Divide | TokenKind::Circ
        ) {
            let token = self.advance();
            let rhs = self.parse_primary()?;
            let op = match token.kind {
                TokenKind::Times => BinaryOp::Times,
                TokenKind::Divide => BinaryOp::Divide,
                TokenKind::Circ => BinaryOp::Circ,
                _ => unreachable!(),
            };
            expr = AstNode::BinaryExpr {
                op,
                left: Box::new(expr),
                right: Box::new(rhs),
            };
        }
        Ok(expr)
    }

    fn parse_primary(&mut self) -> Result<AstNode, LanguageError> {
        match self.current().kind {
            TokenKind::LParen => {
                self.advance();
                let expr = self.parse_expression()?;
                self.expect(TokenKind::RParen)?;
                Ok(expr)
            }
            TokenKind::Pipe => self.parse_cardinality(),
            TokenKind::Rpm => {
                self.advance();
                self.expect(TokenKind::LParen)?;
                let expr = self.parse_expression()?;
                self.expect(TokenKind::RParen)?;
                Ok(AstNode::RpmCall {
                    expr: Box::new(expr),
                })
            }
            TokenKind::Phi => self.parse_fractal(),
            TokenKind::Co => self.parse_state(),
            TokenKind::StateRef => {
                let token = self.advance();
                Ok(AstNode::StateLiteral {
                    operator: token.value[1..].parse::<u8>().unwrap(),
                    domain: token.value[..1].to_string(),
                    drive: None,
                    domain_explicit: true,
                })
            }
            TokenKind::String => Ok(AstNode::StringLiteral {
                value: decode_string_literal(&self.advance().value),
            }),
            TokenKind::Number => Ok(AstNode::NumberLiteral {
                value: self.advance().value.parse::<i64>().unwrap(),
            }),
            TokenKind::EmptySet => {
                self.advance();
                Ok(AstNode::EmptySetLiteral)
            }
            TokenKind::Domain => Ok(AstNode::MetaSymbol {
                name: self.advance().value,
                symbol_kind: "domain".to_string(),
            }),
            TokenKind::Ident => {
                let name = self.advance().value;
                if self.current().kind == TokenKind::LParen {
                    self.advance();
                    let mut args = Vec::new();
                    if self.current().kind != TokenKind::RParen {
                        loop {
                            args.push(self.parse_expression()?);
                            if self.current().kind != TokenKind::Comma {
                                break;
                            }
                            self.advance();
                        }
                    }
                    self.expect(TokenKind::RParen)?;
                    Ok(AstNode::CallExpr { callee: name, args })
                } else if let Some(canonical) = canonical_meta_set_name(&name) {
                    Ok(AstNode::MetaSetLiteral {
                        name: canonical.to_string(),
                    })
                } else if matches!(name.as_str(), "T" | "A" | "f" | "E") {
                    Ok(AstNode::MetaSymbol {
                        name,
                        symbol_kind: "register".to_string(),
                    })
                } else {
                    Ok(AstNode::Identifier { name })
                }
            }
            TokenKind::Drive => self.parse_drive_or_drive_register_symbol(),
            _ => Err(LanguageError::new(
                Stage::Parsing,
                format!("unexpected token {:?}", self.current().kind),
                Some(self.current().position),
            )),
        }
    }

    fn parse_state(&mut self) -> Result<AstNode, LanguageError> {
        let token = self.expect(TokenKind::Co)?;
        let mut domain = "P".to_string();
        let mut domain_explicit = false;
        let mut drive = None;
        if self.current().kind == TokenKind::Caret {
            self.advance();
            domain = self.expect(TokenKind::Domain)?.value;
            domain_explicit = true;
        }
        if self.current().kind == TokenKind::Underscore {
            self.advance();
            self.expect(TokenKind::LBrace)?;
            drive = Some(parse_drive_token_value(
                &self.expect(TokenKind::Drive)?.value,
            )?);
            self.expect(TokenKind::RBrace)?;
        }
        Ok(AstNode::StateLiteral {
            operator: token.value[3..].parse::<u8>().unwrap(),
            domain,
            drive,
            domain_explicit,
        })
    }

    fn parse_drive_or_drive_register_symbol(&mut self) -> Result<AstNode, LanguageError> {
        let token = self.expect(TokenKind::Drive)?;
        let drive = parse_drive_token_value(&token.value)?;
        if self.current().kind == TokenKind::Pipe {
            self.advance();
            let reg = self.expect(TokenKind::Ident)?.value;
            if !matches!(reg.as_str(), "T" | "A" | "f" | "E") {
                return Err(LanguageError::new(
                    Stage::Parsing,
                    format!("invalid register {reg}"),
                    Some(token.position),
                ));
            }
            return Ok(AstNode::MetaSymbol {
                name: format!("F{drive}|{reg}"),
                symbol_kind: "drive_register".to_string(),
            });
        }
        Ok(AstNode::DriveLiteral { drive })
    }

    fn parse_cardinality(&mut self) -> Result<AstNode, LanguageError> {
        self.expect(TokenKind::Pipe)?;
        let collection = self.parse_relation()?;
        self.expect(TokenKind::Pipe)?;
        Ok(AstNode::CardinalityExpr {
            collection: Box::new(collection),
        })
    }

    fn parse_fractal(&mut self) -> Result<AstNode, LanguageError> {
        self.expect(TokenKind::Phi)?;
        self.expect(TokenKind::LAngle)?;
        let mut sequence = vec![self.expect(TokenKind::Number)?.value.parse::<u8>().unwrap()];
        while self.current().kind == TokenKind::Colon {
            self.advance();
            sequence.push(self.expect(TokenKind::Number)?.value.parse::<u8>().unwrap());
        }
        self.expect(TokenKind::RAngle)?;
        Ok(AstNode::FractalLiteral { sequence })
    }
}

pub fn parse_tokens(tokens: Vec<LexToken>) -> Result<AstNode, LanguageError> {
    Parser::new(tokens).parse()
}

pub fn parse_source(source: &str) -> Result<AstNode, LanguageError> {
    let tokens = lex(source)?;
    parse_tokens(tokens)
}

pub fn parse_file(path: impl AsRef<Path>) -> Result<AstNode, String> {
    let path = path.as_ref();
    let source = fs::read_to_string(path)
        .map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    parse_source(&source).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_showcase_style_expression() {
        let ast = parse_source("compose(CO-2^C_{F2}, CO-4^C_{F2})").unwrap();
        match ast {
            AstNode::CallExpr { callee, .. } => assert_eq!(callee, "compose"),
            _ => panic!("expected call expression"),
        }
    }

    #[test]
    fn lexes_unicode_fractal_literal() {
        let tokens = lex("let motif = Φ⟨2:4:8⟩").unwrap();
        assert!(tokens.iter().any(|token| token.kind == TokenKind::Phi));
    }
}
