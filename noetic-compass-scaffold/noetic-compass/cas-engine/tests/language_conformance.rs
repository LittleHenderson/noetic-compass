use std::fs;

use cas_engine::language::{compile_expression, compile_file};
use casc_syntax::{lex as frontend_lex, parse_source as frontend_parse, TokenKind};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Fixture {
    name: String,
    input_kind: String,
    input: String,
    expect_valid: bool,
    expect_result_kind: Option<String>,
    expect_final_result_kind: Option<String>,
}

#[test]
fn language_fixtures_match_expected_behavior() {
    let raw = fs::read_to_string("../validation/cas_language_conformance.json")
        .expect("fixture file exists");
    let fixtures: Vec<Fixture> = serde_json::from_str(&raw).expect("fixture json parses");
    for fixture in fixtures {
        let artifact = match fixture.input_kind.as_str() {
            "file" => compile_file(&fixture.input),
            "expression" => compile_expression(&fixture.input),
            other => panic!("unsupported fixture input_kind {other}"),
        };
        assert_eq!(
            artifact.valid, fixture.expect_valid,
            "fixture {}",
            fixture.name
        );
        let json = artifact.to_json();
        if let Some(expected) = fixture.expect_result_kind.as_deref() {
            assert_eq!(json["result"]["kind"], expected, "fixture {}", fixture.name);
        }
        if let Some(expected) = fixture.expect_final_result_kind.as_deref() {
            assert_eq!(
                json["result"]["final_result"]["kind"], expected,
                "fixture {}",
                fixture.name
            );
        }
    }
}

#[test]
fn frontend_parser_stays_in_lockstep_with_engine_ast() {
    let samples = [
        "CO-2^C_{F2} -> CO-5^E_{F4}",
        "fn bridge(x, y) = x -> y; bridge(C2, E5)",
        "let motif: fractal = Phi<2:4:8>; motif",
    ];
    for sample in samples {
        let frontend_ast = frontend_parse(sample).expect("frontend parse succeeds");
        let engine_ast = compile_expression(sample)
            .ast
            .expect("engine parse succeeds");
        assert_eq!(
            serde_json::to_value(frontend_ast).unwrap(),
            serde_json::to_value(engine_ast).unwrap(),
            "sample {sample}"
        );
    }
}

#[test]
fn frontend_lexer_stays_in_lockstep_with_engine_lexer() {
    let sample = "fn bridge(x: state[C], y: state[E]): relation = x -> y";
    let frontend_tokens = frontend_lex(sample)
        .expect("frontend lex succeeds")
        .into_iter()
        .filter(|token| token.kind != TokenKind::Eof)
        .collect::<Vec<_>>();
    let engine_tokens = compile_expression(sample).tokens;
    assert_eq!(
        serde_json::to_value(frontend_tokens).unwrap(),
        serde_json::to_value(engine_tokens).unwrap()
    );
}
