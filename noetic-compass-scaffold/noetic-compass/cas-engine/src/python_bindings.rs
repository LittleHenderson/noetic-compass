//! PyO3 bindings for the CAS Scoring Engine.
//!
//! Exposes the core CAS types and scoring functions to Python via maturin.

use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashMap;

use crate::algebra;
use crate::inversions;
use crate::metric;
use crate::ontology;
use crate::rpm;
use crate::scoring;
use crate::validation;

// ---------------------------------------------------------------------------
// CognitiveOperator
// ---------------------------------------------------------------------------

#[pyclass(name = "CognitiveOperator")]
#[derive(Clone)]
pub struct PyCognitiveOperator {
    inner: ontology::CognitiveOperator,
}

#[pymethods]
impl PyCognitiveOperator {
    #[new]
    fn new(index: usize) -> PyResult<Self> {
        ontology::CognitiveOperator::from_index(index)
            .map(|op| Self { inner: op })
            .ok_or_else(|| {
                PyValueError::new_err(format!("operator index must be 0-9, got {index}"))
            })
    }

    #[getter]
    fn index(&self) -> usize {
        self.inner.index()
    }

    fn involute(&self) -> Self {
        Self {
            inner: self.inner.involute(),
        }
    }

    fn is_self_dual(&self) -> bool {
        self.inner.is_self_dual()
    }

    fn compose(&self, other: &PyCognitiveOperator) -> Self {
        Self {
            inner: self.inner.compose(other.inner),
        }
    }

    fn is_admissible(&self, source_index: usize, target_index: usize) -> PyResult<bool> {
        let src = ontology::CognitiveStateId::from_linear_index(source_index).ok_or_else(|| {
            PyValueError::new_err(format!("source index must be 0-39, got {source_index}"))
        })?;
        let tgt = ontology::CognitiveStateId::from_linear_index(target_index).ok_or_else(|| {
            PyValueError::new_err(format!("target index must be 0-39, got {target_index}"))
        })?;
        Ok(self.inner.is_admissible(src, tgt))
    }

    fn __repr__(&self) -> String {
        format!("CognitiveOperator(CO-{})", self.inner.index())
    }

    fn __eq__(&self, other: &PyCognitiveOperator) -> bool {
        self.inner == other.inner
    }

    #[staticmethod]
    fn all() -> Vec<PyCognitiveOperator> {
        ontology::CognitiveOperator::ALL
            .iter()
            .map(|&op| PyCognitiveOperator { inner: op })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// Domain
// ---------------------------------------------------------------------------

#[pyclass(name = "Domain")]
#[derive(Clone)]
pub struct PyDomain {
    inner: ontology::Domain,
}

#[pymethods]
impl PyDomain {
    #[new]
    fn new(index: usize) -> PyResult<Self> {
        ontology::Domain::from_index(index)
            .map(|d| Self { inner: d })
            .ok_or_else(|| PyValueError::new_err(format!("domain index must be 0-3, got {index}")))
    }

    #[getter]
    fn index(&self) -> usize {
        self.inner.index()
    }

    #[getter]
    fn name(&self) -> String {
        format!("{}", self.inner)
    }

    #[getter]
    fn abbreviation(&self) -> String {
        self.inner.abbreviation().to_string()
    }

    fn dominates(&self, other: &PyDomain) -> bool {
        self.inner.dominates(other.inner)
    }

    fn __repr__(&self) -> String {
        format!("Domain({})", self.inner)
    }

    fn __eq__(&self, other: &PyDomain) -> bool {
        self.inner == other.inner
    }

    #[staticmethod]
    fn all() -> Vec<PyDomain> {
        ontology::Domain::ALL
            .iter()
            .map(|&d| PyDomain { inner: d })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// CoreDrive
// ---------------------------------------------------------------------------

#[pyclass(name = "CoreDrive")]
#[derive(Clone)]
pub struct PyCoreDrive {
    inner: ontology::CoreDrive,
}

#[pymethods]
impl PyCoreDrive {
    #[new]
    fn new(number: u8) -> PyResult<Self> {
        ontology::CoreDrive::from_number(number)
            .map(|d| Self { inner: d })
            .ok_or_else(|| PyValueError::new_err(format!("drive number must be 1-7, got {number}")))
    }

    #[getter]
    fn number(&self) -> u8 {
        self.inner.number()
    }

    #[getter]
    fn name(&self) -> &'static str {
        self.inner.name()
    }

    fn invert(&self) -> Self {
        Self {
            inner: self.inner.invert(),
        }
    }

    fn is_self_dual(&self) -> bool {
        self.inner.is_self_dual()
    }

    fn __repr__(&self) -> String {
        format!("CoreDrive(F{} {})", self.inner.number(), self.inner.name())
    }

    fn __eq__(&self, other: &PyCoreDrive) -> bool {
        self.inner == other.inner
    }

    #[staticmethod]
    fn all() -> Vec<PyCoreDrive> {
        ontology::CoreDrive::ALL
            .iter()
            .map(|&d| PyCoreDrive { inner: d })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// Register (CAS v7.5 Phenomenological Register, Clarification 8)
// ---------------------------------------------------------------------------

/// Phenomenological Register (CAS v7.5). Canonical short forms: "T", "A",
/// "f" (lowercase — authoritative per Clarification 8 Section 3), "E".
#[pyclass(name = "Register", eq, hash, frozen)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyRegister {
    inner: ontology::Register,
}

#[pymethods]
impl PyRegister {
    /// Construct a Register from its canonical short-form symbol
    /// ("T", "A", "f", "E"). The affective symbol is LOWERCASE.
    #[new]
    fn new(symbol: &str) -> PyResult<Self> {
        ontology::Register::from_symbol(symbol)
            .map(|inner| Self { inner })
            .ok_or_else(|| {
                PyValueError::new_err(format!(
                    "register symbol must be one of 'T', 'A', 'f', 'E'; got {symbol:?}"
                ))
            })
    }

    #[getter]
    fn symbol(&self) -> &'static str {
        self.inner.symbol()
    }

    #[getter]
    fn name(&self) -> &'static str {
        self.inner.name()
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Transcendent() -> Self {
        Self {
            inner: ontology::Register::Transcendent,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Analytical() -> Self {
        Self {
            inner: ontology::Register::Analytical,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Affective() -> Self {
        Self {
            inner: ontology::Register::Affective,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Embodied() -> Self {
        Self {
            inner: ontology::Register::Embodied,
        }
    }

    fn __repr__(&self) -> String {
        format!("Register({})", self.inner.symbol())
    }

    fn __str__(&self) -> String {
        self.inner.symbol().to_string()
    }

    #[staticmethod]
    fn all() -> Vec<PyRegister> {
        ontology::Register::ALL
            .iter()
            .map(|&r| PyRegister { inner: r })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// CognitiveStateVector
// ---------------------------------------------------------------------------

#[pyclass(name = "CognitiveStateVector")]
#[derive(Clone)]
pub struct PyCognitiveStateVector {
    inner: ontology::CognitiveStateVector,
}

#[pymethods]
impl PyCognitiveStateVector {
    #[new]
    fn new(probabilities: Vec<f64>) -> PyResult<Self> {
        if probabilities.len() != ontology::NUM_STATES {
            return Err(PyValueError::new_err(format!(
                "expected {} probabilities, got {}",
                ontology::NUM_STATES,
                probabilities.len()
            )));
        }
        let mut arr = [0.0f64; ontology::NUM_STATES];
        arr.copy_from_slice(&probabilities);
        ontology::CognitiveStateVector::new(arr)
            .map(|v| Self { inner: v })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    #[staticmethod]
    fn uniform() -> Self {
        Self {
            inner: ontology::CognitiveStateVector::uniform(),
        }
    }

    fn probability_at(&self, index: usize) -> PyResult<f64> {
        if index >= ontology::NUM_STATES {
            return Err(PyIndexError::new_err(format!(
                "index must be 0-39, got {index}"
            )));
        }
        Ok(self.inner.probability_at(index))
    }

    fn domain_average(&self, domain_index: usize) -> PyResult<f64> {
        let domain = ontology::Domain::from_index(domain_index).ok_or_else(|| {
            PyValueError::new_err(format!("domain index must be 0-3, got {domain_index}"))
        })?;
        Ok(self.inner.domain_average(domain))
    }

    fn as_list(&self) -> Vec<f64> {
        self.inner.as_slice().to_vec()
    }

    /// CAS v7.5: Return a copy of this state vector annotated with the given
    /// Phenomenological Register.
    fn with_register(&self, register: &PyRegister) -> Self {
        Self {
            inner: self.inner.clone().with_register(register.inner),
        }
    }

    /// CAS v7.5: Return a copy of this state vector with no Register
    /// annotation (register-neutral / v7.4-compatible).
    fn without_register(&self) -> Self {
        Self {
            inner: self.inner.clone().without_register(),
        }
    }

    /// CAS v7.5: The Phenomenological Register annotation, if any.
    /// Returns `None` for register-neutral (v7.4-compatible) vectors.
    #[getter]
    fn register(&self) -> Option<PyRegister> {
        self.inner.register().map(|r| PyRegister { inner: r })
    }

    fn __repr__(&self) -> String {
        format!("CognitiveStateVector(len={})", ontology::NUM_STATES)
    }
}

// ---------------------------------------------------------------------------
// DialConfig
// ---------------------------------------------------------------------------

#[pyclass(name = "DialConfig")]
#[derive(Clone)]
pub struct PyDialConfig {
    inner: ontology::DialConfig,
}

#[pymethods]
impl PyDialConfig {
    #[new]
    fn new(values: Vec<u8>) -> PyResult<Self> {
        if values.len() != 10 {
            return Err(PyValueError::new_err(format!(
                "expected 10 dial values, got {}",
                values.len()
            )));
        }
        let mut arr = [0u8; 10];
        arr.copy_from_slice(&values);
        ontology::DialConfig::new(arr)
            .map(|c| Self { inner: c })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    #[staticmethod]
    fn default_config() -> Self {
        Self {
            inner: ontology::DialConfig::default_config(),
        }
    }

    fn get(&self, operator_index: usize) -> PyResult<u8> {
        let op = ontology::CognitiveOperator::from_index(operator_index).ok_or_else(|| {
            PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}"))
        })?;
        Ok(self.inner.get(op).value())
    }

    fn set(&mut self, operator_index: usize, value: u8) -> PyResult<()> {
        let op = ontology::CognitiveOperator::from_index(operator_index).ok_or_else(|| {
            PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}"))
        })?;
        self.inner
            .set(op, value)
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    fn as_list(&self) -> Vec<u8> {
        ontology::CognitiveOperator::ALL
            .iter()
            .map(|&op| self.inner.get(op).value())
            .collect()
    }

    fn __repr__(&self) -> String {
        let vals: Vec<u8> = self.as_list();
        format!("DialConfig({vals:?})")
    }
}

// ---------------------------------------------------------------------------
// OperatorScores
// ---------------------------------------------------------------------------

#[pyclass(name = "OperatorScores")]
#[derive(Clone)]
pub struct PyOperatorScores {
    inner: scoring::OperatorScores,
}

#[pymethods]
impl PyOperatorScores {
    #[new]
    fn new(scores: Vec<f64>) -> PyResult<Self> {
        if scores.len() != 10 {
            return Err(PyValueError::new_err(format!(
                "expected 10 scores, got {}",
                scores.len()
            )));
        }
        let mut arr = [0.0f64; 10];
        arr.copy_from_slice(&scores);
        scoring::OperatorScores::new(arr)
            .map(|s| Self { inner: s })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    fn profile_score(&self) -> f64 {
        self.inner.profile_score()
    }

    fn involution_balance(&self, a_index: usize, b_index: usize) -> PyResult<f64> {
        let a = ontology::CognitiveOperator::from_index(a_index)
            .ok_or_else(|| PyValueError::new_err("operator index must be 0-9"))?;
        let b = ontology::CognitiveOperator::from_index(b_index)
            .ok_or_else(|| PyValueError::new_err("operator index must be 0-9"))?;
        Ok(self.inner.involution_balance(a, b))
    }

    fn average(&self) -> f64 {
        self.inner.average()
    }

    fn all_involution_balances(&self) -> Vec<f64> {
        self.inner.all_involution_balances().to_vec()
    }

    fn get(&self, operator_index: usize) -> PyResult<f64> {
        let op = ontology::CognitiveOperator::from_index(operator_index)
            .ok_or_else(|| PyValueError::new_err("operator index must be 0-9"))?;
        Ok(self.inner.get(op))
    }
}

// ---------------------------------------------------------------------------
// DomainCoherence
// ---------------------------------------------------------------------------

#[pyclass(name = "DomainCoherence")]
#[derive(Clone)]
pub struct PyDomainCoherence {
    inner: scoring::DomainCoherence,
}

#[pymethods]
impl PyDomainCoherence {
    #[staticmethod]
    fn from_averages(averages: Vec<f64>) -> PyResult<Self> {
        if averages.len() != 4 {
            return Err(PyValueError::new_err(format!(
                "expected 4 domain averages, got {}",
                averages.len()
            )));
        }
        let mut arr = [0.0f64; 4];
        arr.copy_from_slice(&averages);
        Ok(Self {
            inner: scoring::DomainCoherence::from_averages(arr),
        })
    }

    #[staticmethod]
    fn from_state_vector(state: &PyCognitiveStateVector) -> Self {
        Self {
            inner: scoring::DomainCoherence::from_state_vector(&state.inner),
        }
    }

    fn dci(&self) -> f64 {
        self.inner.dci()
    }

    fn domain_averages(&self) -> Vec<f64> {
        self.inner.domain_averages().to_vec()
    }

    fn weakest_domain(&self) -> PyDomain {
        PyDomain {
            inner: self.inner.weakest_domain(),
        }
    }

    fn strongest_domain(&self) -> PyDomain {
        PyDomain {
            inner: self.inner.strongest_domain(),
        }
    }
}

// ---------------------------------------------------------------------------
// InversionScanner
// ---------------------------------------------------------------------------

#[pyclass(name = "InversionScanner")]
pub struct PyInversionScanner;

#[pymethods]
impl PyInversionScanner {
    #[new]
    fn new() -> Self {
        Self
    }

    #[staticmethod]
    #[pyo3(signature = (operator_scores, drive_scores, state_vector, domain_averages, domain_drive_scores=None, pathway_scores=None))]
    fn scan(
        operator_scores: Vec<f64>,
        drive_scores: Vec<f64>,
        state_vector: &PyCognitiveStateVector,
        domain_averages: Vec<f64>,
        domain_drive_scores: Option<Vec<Vec<f64>>>,
        pathway_scores: Option<Vec<Vec<f64>>>,
    ) -> PyResult<HashMap<String, PyObject>> {
        if operator_scores.len() != 10 {
            return Err(PyValueError::new_err("expected 10 operator scores"));
        }
        if drive_scores.len() != 7 {
            return Err(PyValueError::new_err("expected 7 drive scores"));
        }
        if domain_averages.len() != 4 {
            return Err(PyValueError::new_err("expected 4 domain averages"));
        }

        let mut op_arr = [0.0f64; 10];
        op_arr.copy_from_slice(&operator_scores);

        let mut drv_arr = [0.0f64; 7];
        drv_arr.copy_from_slice(&drive_scores);
        let drv_profile = ontology::DriveProfile::new(drv_arr)
            .ok_or_else(|| PyValueError::new_err("invalid drive scores"))?;

        let mut dom_arr = [0.0f64; 4];
        dom_arr.copy_from_slice(&domain_averages);

        // Parse domain_drive_scores: 7x4 matrix, default to uniform
        let dds = if let Some(ref dds_vec) = domain_drive_scores {
            if dds_vec.len() != 7 {
                return Err(PyValueError::new_err(
                    "domain_drive_scores must have 7 rows",
                ));
            }
            let mut arr = [[0.5f64; 4]; 7];
            for (i, row) in dds_vec.iter().enumerate() {
                if row.len() != 4 {
                    return Err(PyValueError::new_err(
                        "each domain_drive_scores row must have 4 values",
                    ));
                }
                arr[i].copy_from_slice(row);
            }
            arr
        } else {
            // Default: all scores match the core drive scores across domains
            let mut arr = [[0.5f64; 4]; 7];
            for (i, &s) in drv_arr.iter().enumerate() {
                arr[i] = [s; 4];
            }
            arr
        };

        // Parse pathway_scores: 7x4 matrix, default to uniform 0.5
        let ps = if let Some(ref ps_vec) = pathway_scores {
            if ps_vec.len() != 7 {
                return Err(PyValueError::new_err("pathway_scores must have 7 rows"));
            }
            let mut arr = [[0.5f64; 4]; 7];
            for (i, row) in ps_vec.iter().enumerate() {
                if row.len() != 4 {
                    return Err(PyValueError::new_err(
                        "each pathway_scores row must have 4 values",
                    ));
                }
                arr[i].copy_from_slice(row);
            }
            arr
        } else {
            [[0.5f64; 4]; 7]
        };

        let input = inversions::InversionScanInput {
            operator_scores: op_arr,
            domain_averages: dom_arr,
            drive_profile: drv_profile,
            state_vector: state_vector.inner.clone(),
            domain_drive_scores: dds,
            pathway_scores: ps,
        };

        let scanner = inversions::InversionScanner::new();
        let result = scanner
            .scan(&input)
            .map_err(|e| PyValueError::new_err(format!("{e}")))?;

        Python::with_gil(|py| {
            let mut map: HashMap<String, PyObject> = HashMap::new();

            let axis_scores: Vec<f64> = result.axis_scores().to_vec();
            map.insert(
                "axis_scores".to_string(),
                axis_scores.into_pyobject(py)?.into(),
            );
            map.insert(
                "stealth_resistance".to_string(),
                result.stealth_resistance().into_pyobject(py)?.into(),
            );
            map.insert(
                "compound_severity".to_string(),
                result.compound_severity().into_pyobject(py)?.into(),
            );

            let resistance_input = result.to_resistance_input();
            map.insert(
                "resistance_score".to_string(),
                resistance_input
                    .resistance_score()
                    .into_pyobject(py)?
                    .into(),
            );

            Ok(map)
        })
    }
}

// ---------------------------------------------------------------------------
// RpmProfile
// ---------------------------------------------------------------------------

#[pyclass(name = "RpmProfile")]
#[derive(Clone)]
pub struct PyRpmProfile {
    inner: rpm::RpmProfile,
}

#[pymethods]
impl PyRpmProfile {
    /// Create an RpmProfile.
    ///
    /// Args:
    ///   a0_score: The shared A0 (Pure Desire) score in [0, 1]
    ///   drive_scores: 7 lists of 3 floats each: [Dn, Wn, Pn] per drive (F1..F7)
    ///   threshold: Satisfaction threshold in [0, 1] (default 0.5)
    #[new]
    fn new(a0_score: f64, drive_scores: Vec<Vec<f64>>, threshold: Option<f64>) -> PyResult<Self> {
        if drive_scores.len() != 7 {
            return Err(PyValueError::new_err(format!(
                "expected 7 drive score vectors, got {}",
                drive_scores.len()
            )));
        }
        let thresh = threshold.unwrap_or(0.5);

        let mut ds = [[0.0f64; 3]; 7];
        for (i, row) in drive_scores.iter().enumerate() {
            if row.len() != 3 {
                return Err(PyValueError::new_err(format!(
                    "each drive score vector must have 3 values [Dn, Wn, Pn], got {}",
                    row.len()
                )));
            }
            ds[i].copy_from_slice(row);
        }

        rpm::RpmProfile::new(a0_score, ds, thresh)
            .map(|p| Self { inner: p })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    fn overall_completeness(&self) -> f64 {
        self.inner.overall_completeness()
    }

    fn chain_completeness(&self, drive_number: u8) -> PyResult<f64> {
        let drive = ontology::CoreDrive::from_number(drive_number).ok_or_else(|| {
            PyValueError::new_err(format!("drive number must be 1-7, got {drive_number}"))
        })?;
        Ok(self.inner.chain(drive).completeness())
    }

    fn a0_satisfied(&self) -> bool {
        self.inner.a0_satisfied()
    }

    fn per_drive_completeness(&self) -> Vec<f64> {
        self.inner.per_drive_completeness().to_vec()
    }

    fn completed_chain_count(&self) -> usize {
        self.inner.completed_chain_count()
    }
}

// ---------------------------------------------------------------------------
// compute_nccs
// ---------------------------------------------------------------------------

#[pyfunction]
fn compute_nccs(
    operator_scores: Vec<f64>,
    domain_averages: Vec<f64>,
    drive_scores: Vec<f64>,
    rpm_completeness: f64,
    pathway_rpm_completeness: f64,
    bias_flag_count: u32,
    inversion_axis_scores: Vec<f64>,
    stealth_resistance: f64,
    compound_severity: f64,
    manipulation_resistance: f64,
    overton_drift_resistance: f64,
) -> PyResult<HashMap<String, PyObject>> {
    // Validate and convert
    if operator_scores.len() != 10 {
        return Err(PyValueError::new_err("expected 10 operator scores"));
    }
    if domain_averages.len() != 4 {
        return Err(PyValueError::new_err("expected 4 domain averages"));
    }
    if drive_scores.len() != 7 {
        return Err(PyValueError::new_err("expected 7 drive scores"));
    }
    if inversion_axis_scores.len() != 7 {
        return Err(PyValueError::new_err("expected 7 inversion axis scores"));
    }

    let mut op_arr = [0.0f64; 10];
    op_arr.copy_from_slice(&operator_scores);
    let op =
        scoring::OperatorScores::new(op_arr).map_err(|e| PyValueError::new_err(format!("{e}")))?;

    let mut dom_arr = [0.0f64; 4];
    dom_arr.copy_from_slice(&domain_averages);
    let dc = scoring::DomainCoherence::from_averages(dom_arr);

    let mut drv_arr = [0.0f64; 7];
    drv_arr.copy_from_slice(&drive_scores);
    let dp = ontology::DriveProfile::new(drv_arr)
        .ok_or_else(|| PyValueError::new_err("invalid drive scores (must be in [0, 1])"))?;

    let mut inv_arr = [0.0f64; 7];
    inv_arr.copy_from_slice(&inversion_axis_scores);
    let ir = scoring::InversionResistanceInput::new(inv_arr, stealth_resistance, compound_severity)
        .map_err(|e| PyValueError::new_err(format!("{e}")))?;

    let se =
        scoring::SocialEngineeringInput::new(manipulation_resistance, overton_drift_resistance)
            .map_err(|e| PyValueError::new_err(format!("{e}")))?;

    let pq = scoring::PathwayQualityInput::new(pathway_rpm_completeness, bias_flag_count)
        .map_err(|e| PyValueError::new_err(format!("{e}")))?;

    let input = scoring::NccsInput {
        operator_scores: op,
        domain_coherence: dc,
        drive_profile: dp,
        rpm_completeness,
        pathway_quality: pq,
        inversion_resistance: ir,
        social_engineering: se,
    };

    let result = scoring::compute_nccs(&input);

    Python::with_gil(|py| {
        let mut map: HashMap<String, PyObject> = HashMap::new();
        map.insert(
            "operator_profile".to_string(),
            result.operator_profile.into_pyobject(py)?.into(),
        );
        map.insert(
            "domain_coherence".to_string(),
            result.domain_coherence.into_pyobject(py)?.into(),
        );
        map.insert(
            "drive_rpm_integrity".to_string(),
            result.drive_rpm_integrity.into_pyobject(py)?.into(),
        );
        map.insert(
            "pathway_quality".to_string(),
            result.pathway_quality.into_pyobject(py)?.into(),
        );
        map.insert(
            "inversion_resistance".to_string(),
            result.inversion_resistance.into_pyobject(py)?.into(),
        );
        map.insert(
            "social_engineering".to_string(),
            result.social_engineering.into_pyobject(py)?.into(),
        );
        map.insert(
            "composite".to_string(),
            result.composite.into_pyobject(py)?.into(),
        );
        map.insert(
            "certification".to_string(),
            format!("{}", result.certification)
                .into_pyobject(py)?
                .into(),
        );
        Ok(map)
    })
}

// ---------------------------------------------------------------------------
// Metric functions
// ---------------------------------------------------------------------------

#[pyfunction]
fn geodesic_distance(p: &PyCognitiveStateVector, q: &PyCognitiveStateVector) -> f64 {
    metric::geodesic_distance(&p.inner, &q.inner)
}

#[pyfunction]
fn bhattacharyya_coefficient(p: &PyCognitiveStateVector, q: &PyCognitiveStateVector) -> f64 {
    metric::bhattacharyya_coefficient(&p.inner, &q.inner)
}

// ---------------------------------------------------------------------------
// Algebra functions
// ---------------------------------------------------------------------------

/// Multiply two cognitive state vectors on the open simplex.
/// Uses element-wise geometric mean, renormalized to Δ°39.
#[pyfunction]
fn multiply_state_vectors(p: Vec<f64>, q: Vec<f64>) -> PyResult<Vec<f64>> {
    algebra::simplex_multiply(&p, &q)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Divide two cognitive state vectors on the open simplex.
/// Uses element-wise ratio, renormalized to Δ°39.
#[pyfunction]
fn divide_state_vectors(p: Vec<f64>, q: Vec<f64>) -> PyResult<Vec<f64>> {
    algebra::simplex_divide(&p, &q)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Multiply two cognitive states (operator, domain, drive).
/// Returns (result_operator_idx, result_domain_idx, result_drive_number) or raises ValueError.
#[pyfunction]
fn multiply_cognitive_states(
    left_op: usize, left_dom: usize, left_drive: u8,
    right_op: usize, right_dom: usize, right_drive: u8,
) -> PyResult<(usize, usize, u8)> {
    let lo = ontology::CognitiveOperator::from_index(left_op)
        .ok_or_else(|| PyValueError::new_err(format!("invalid operator index {left_op}")))?;
    let ld = ontology::Domain::from_index(left_dom)
        .ok_or_else(|| PyValueError::new_err(format!("invalid domain index {left_dom}")))?;
    let ldr = ontology::CoreDrive::from_number(left_drive)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive number {left_drive}")))?;
    let ro = ontology::CognitiveOperator::from_index(right_op)
        .ok_or_else(|| PyValueError::new_err(format!("invalid operator index {right_op}")))?;
    let rd = ontology::Domain::from_index(right_dom)
        .ok_or_else(|| PyValueError::new_err(format!("invalid domain index {right_dom}")))?;
    let rdr = ontology::CoreDrive::from_number(right_drive)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive number {right_drive}")))?;

    let left = ontology::CognitiveStateId::new(lo, ld);
    let right = ontology::CognitiveStateId::new(ro, rd);

    let (result, drive) = algebra::multiply_states(left, ldr, right, rdr)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok((result.operator().index(), result.domain().index(), drive.number()))
}

/// Divide two cognitive states (operator, domain, drive).
/// Returns (result_operator_idx, result_domain_idx, result_drive_number) or raises ValueError.
#[pyfunction]
fn divide_cognitive_states(
    left_op: usize, left_dom: usize, left_drive: u8,
    right_op: usize, right_dom: usize, right_drive: u8,
) -> PyResult<(usize, usize, u8)> {
    let lo = ontology::CognitiveOperator::from_index(left_op)
        .ok_or_else(|| PyValueError::new_err(format!("invalid operator index {left_op}")))?;
    let ld = ontology::Domain::from_index(left_dom)
        .ok_or_else(|| PyValueError::new_err(format!("invalid domain index {left_dom}")))?;
    let ldr = ontology::CoreDrive::from_number(left_drive)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive number {left_drive}")))?;
    let ro = ontology::CognitiveOperator::from_index(right_op)
        .ok_or_else(|| PyValueError::new_err(format!("invalid operator index {right_op}")))?;
    let rd = ontology::Domain::from_index(right_dom)
        .ok_or_else(|| PyValueError::new_err(format!("invalid domain index {right_dom}")))?;
    let rdr = ontology::CoreDrive::from_number(right_drive)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive number {right_drive}")))?;

    let left = ontology::CognitiveStateId::new(lo, ld);
    let right = ontology::CognitiveStateId::new(ro, rd);

    let (result, drive) = algebra::divide_states(left, ldr, right, rdr)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok((result.operator().index(), result.domain().index(), drive.number()))
}

/// Synthesize two drives under CAS algebra.
/// Returns the result drive number (1-7).
#[pyfunction]
fn synthesize_drives(drive_a: u8, drive_b: u8) -> PyResult<u8> {
    let a = ontology::CoreDrive::from_number(drive_a)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive {drive_a}")))?;
    let b = ontology::CoreDrive::from_number(drive_b)
        .ok_or_else(|| PyValueError::new_err(format!("invalid drive {drive_b}")))?;
    Ok(algebra::synthesize_drives(a, b).number())
}

// ---------------------------------------------------------------------------
// CAS v7.6 Production Semantics bindings (Clarification 9)
// ---------------------------------------------------------------------------
//
// The Production Semantics types live in `ontology::recipe` and the
// yield-calculation algorithms live in `scoring::yield_calc`. These are
// additive over v7.4/v7.5 and do not modify existing types. Follow the
// PyRegister pattern established in v7.5.

use crate::ontology::recipe as recipe_mod;
use crate::scoring::yield_calc as yield_mod;

/// PyO3 wrapper for [`crate::ontology::recipe::PrimitiveId`]. Construct via
/// the class methods (`noetic`, `domain`, `drive`, `register`, `compound`);
/// register-annotated variants accept a symbol string ("T"/"A"/"f"/"E") per
/// Clarification 8 Section 3 (lowercase `f` is authoritative).
#[pyclass(name = "PrimitiveId", eq, hash, frozen)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyPrimitiveId {
    inner: recipe_mod::PrimitiveId,
}

impl PyPrimitiveId {
    fn parse_register(symbol: Option<&str>) -> PyResult<Option<ontology::Register>> {
        match symbol {
            None => Ok(None),
            Some(s) => ontology::Register::from_symbol(s)
                .map(Some)
                .ok_or_else(|| {
                    PyValueError::new_err(format!(
                        "register symbol must be one of 'T', 'A', 'f', 'E'; got {s:?}"
                    ))
                }),
        }
    }
}

#[pymethods]
impl PyPrimitiveId {
    /// Construct a pure Noetic primitive `^n` (or `^n|R` if `register` is
    /// given). `operator_index` is the CO-k index in [0, 9].
    #[staticmethod]
    #[pyo3(signature = (operator_index, register=None))]
    fn noetic(operator_index: usize, register: Option<&str>) -> PyResult<Self> {
        let op = ontology::CognitiveOperator::from_index(operator_index).ok_or_else(|| {
            PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}"))
        })?;
        let reg = Self::parse_register(register)?;
        let inner = match reg {
            None => recipe_mod::PrimitiveId::noetic(op),
            Some(r) => recipe_mod::PrimitiveId::noetic_with_register(op, r),
        };
        Ok(Self { inner })
    }

    /// Construct a pure Domain primitive `^D` (or `^D|R` if `register` is
    /// given). `domain_index` in [0, 3] (P=0, C=1, E=2, O=3).
    #[staticmethod]
    #[pyo3(signature = (domain_index, register=None))]
    fn domain(domain_index: usize, register: Option<&str>) -> PyResult<Self> {
        let d = ontology::Domain::from_index(domain_index).ok_or_else(|| {
            PyValueError::new_err(format!("domain index must be 0-3, got {domain_index}"))
        })?;
        let reg = Self::parse_register(register)?;
        let inner = match reg {
            None => recipe_mod::PrimitiveId::domain(d),
            Some(r) => recipe_mod::PrimitiveId::domain_with_register(d, r),
        };
        Ok(Self { inner })
    }

    /// Construct a pure Drive primitive `F_k` (or `F_k|R` if `register` is
    /// given). `drive_number` in [1, 7].
    #[staticmethod]
    #[pyo3(signature = (drive_number, register=None))]
    fn drive(drive_number: u8, register: Option<&str>) -> PyResult<Self> {
        let d = ontology::CoreDrive::from_number(drive_number).ok_or_else(|| {
            PyValueError::new_err(format!("drive number must be 1-7, got {drive_number}"))
        })?;
        let reg = Self::parse_register(register)?;
        let inner = match reg {
            None => recipe_mod::PrimitiveId::drive(d),
            Some(r) => recipe_mod::PrimitiveId::drive_with_register(d, r),
        };
        Ok(Self { inner })
    }

    /// Construct a Register-only primitive `|R`. `register` is a symbol.
    #[staticmethod]
    fn register(register: &str) -> PyResult<Self> {
        let r = ontology::Register::from_symbol(register).ok_or_else(|| {
            PyValueError::new_err(format!(
                "register symbol must be one of 'T', 'A', 'f', 'E'; got {register:?}"
            ))
        })?;
        Ok(Self {
            inner: recipe_mod::PrimitiveId::register(r),
        })
    }

    /// Construct a compound primitive `^n^D_{F_k}` (or `...|R` if `register`
    /// is given).
    #[staticmethod]
    #[pyo3(signature = (operator_index, domain_index, drive_number, register=None))]
    fn compound(
        operator_index: usize,
        domain_index: usize,
        drive_number: u8,
        register: Option<&str>,
    ) -> PyResult<Self> {
        let op = ontology::CognitiveOperator::from_index(operator_index).ok_or_else(|| {
            PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}"))
        })?;
        let d = ontology::Domain::from_index(domain_index).ok_or_else(|| {
            PyValueError::new_err(format!("domain index must be 0-3, got {domain_index}"))
        })?;
        let drv = ontology::CoreDrive::from_number(drive_number).ok_or_else(|| {
            PyValueError::new_err(format!("drive number must be 1-7, got {drive_number}"))
        })?;
        let reg = Self::parse_register(register)?;
        let inner = match reg {
            None => recipe_mod::PrimitiveId::compound(op, d, drv),
            Some(r) => recipe_mod::PrimitiveId::compound_with_register(op, d, drv, r),
        };
        Ok(Self { inner })
    }

    #[getter]
    fn canonical_notation(&self) -> String {
        self.inner.canonical_notation()
    }

    #[getter]
    fn register_symbol(&self) -> Option<&'static str> {
        self.inner.register_annotation().map(|r| r.symbol())
    }

    fn __repr__(&self) -> String {
        format!("PrimitiveId({})", self.inner.canonical_notation())
    }

    fn __str__(&self) -> String {
        self.inner.canonical_notation()
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::ProductionTarget`].
#[pyclass(name = "ProductionTarget")]
#[derive(Clone)]
pub struct PyProductionTarget {
    inner: recipe_mod::ProductionTarget,
}

#[pymethods]
impl PyProductionTarget {
    #[new]
    fn new(name: String) -> Self {
        Self {
            inner: recipe_mod::ProductionTarget::new(name),
        }
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }

    fn __repr__(&self) -> String {
        format!("ProductionTarget(Ω_{{{}}})", self.inner.name)
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::Leakage`].
#[pyclass(name = "Leakage")]
#[derive(Clone)]
pub struct PyLeakage {
    inner: recipe_mod::Leakage,
}

#[pymethods]
impl PyLeakage {
    #[new]
    fn new(prerequisite: &PyPrimitiveId, side_product: String, magnitude: f64) -> Self {
        Self {
            inner: recipe_mod::Leakage::new(prerequisite.inner, side_product, magnitude),
        }
    }

    #[getter]
    fn side_product(&self) -> String {
        self.inner.side_product.clone()
    }

    #[getter]
    fn magnitude(&self) -> f64 {
        self.inner.magnitude
    }

    #[getter]
    fn prerequisite(&self) -> PyPrimitiveId {
        PyPrimitiveId {
            inner: self.inner.prerequisite,
        }
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::Catalyst`].
#[pyclass(name = "Catalyst")]
#[derive(Clone)]
pub struct PyCatalyst {
    inner: recipe_mod::Catalyst,
}

#[pymethods]
impl PyCatalyst {
    #[new]
    fn new(name: String) -> Self {
        Self {
            inner: recipe_mod::Catalyst::new(name),
        }
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::Inhibitor`].
#[pyclass(name = "Inhibitor")]
#[derive(Clone)]
pub struct PyInhibitor {
    inner: recipe_mod::Inhibitor,
}

#[pymethods]
impl PyInhibitor {
    #[new]
    fn new(name: String) -> Self {
        Self {
            inner: recipe_mod::Inhibitor::new(name),
        }
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::Conditions`].
#[pyclass(name = "Conditions")]
#[derive(Clone)]
pub struct PyConditions {
    inner: recipe_mod::Conditions,
}

#[pymethods]
impl PyConditions {
    #[new]
    #[pyo3(signature = (catalysts=None, inhibitors=None))]
    fn new(catalysts: Option<Vec<PyCatalyst>>, inhibitors: Option<Vec<PyInhibitor>>) -> Self {
        let cats = catalysts
            .unwrap_or_default()
            .into_iter()
            .map(|c| c.inner)
            .collect();
        let inhs = inhibitors
            .unwrap_or_default()
            .into_iter()
            .map(|i| i.inner)
            .collect();
        Self {
            inner: recipe_mod::Conditions::new(cats, inhs),
        }
    }

    #[staticmethod]
    fn empty() -> Self {
        Self {
            inner: recipe_mod::Conditions::empty(),
        }
    }

    #[getter]
    fn catalyst_names(&self) -> Vec<String> {
        self.inner
            .catalysts
            .iter()
            .map(|c| c.name.clone())
            .collect()
    }

    #[getter]
    fn inhibitor_names(&self) -> Vec<String> {
        self.inner
            .inhibitors
            .iter()
            .map(|i| i.name.clone())
            .collect()
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::Recipe`].
#[pyclass(name = "Recipe")]
#[derive(Clone)]
pub struct PyRecipe {
    inner: recipe_mod::Recipe,
}

#[pymethods]
impl PyRecipe {
    /// Construct a Recipe.
    ///
    /// `prerequisites` is a list of `(PrimitiveId, coefficient)` tuples.
    /// `leakages` and `conditions` are optional.
    #[new]
    #[pyo3(signature = (target, prerequisites, leakages=None, conditions=None))]
    fn new(
        target: &PyProductionTarget,
        prerequisites: Vec<(PyPrimitiveId, f64)>,
        leakages: Option<Vec<PyLeakage>>,
        conditions: Option<PyConditions>,
    ) -> Self {
        let prereq: Vec<(recipe_mod::PrimitiveId, f64)> = prerequisites
            .into_iter()
            .map(|(p, c)| (p.inner, c))
            .collect();
        let leaks: Vec<recipe_mod::Leakage> = leakages
            .unwrap_or_default()
            .into_iter()
            .map(|l| l.inner)
            .collect();
        let conds = conditions
            .map(|c| c.inner)
            .unwrap_or_else(recipe_mod::Conditions::empty);
        Self {
            inner: recipe_mod::Recipe::with_leakages_and_conditions(
                target.inner.clone(),
                prereq,
                leaks,
                conds,
            ),
        }
    }

    #[getter]
    fn target(&self) -> PyProductionTarget {
        PyProductionTarget {
            inner: self.inner.target.clone(),
        }
    }

    #[getter]
    fn arity(&self) -> usize {
        self.inner.arity()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Return the list of `(PrimitiveId, coefficient)` prerequisite pairs.
    fn prerequisites(&self) -> Vec<(PyPrimitiveId, f64)> {
        self.inner
            .prerequisites
            .iter()
            .map(|(p, c)| (PyPrimitiveId { inner: *p }, *c))
            .collect()
    }

    /// Return the list of Leakage entries.
    fn leakages(&self) -> Vec<PyLeakage> {
        self.inner
            .leakages
            .iter()
            .cloned()
            .map(|l| PyLeakage { inner: l })
            .collect()
    }

    /// Return the Conditions (catalysts + inhibitors).
    fn conditions(&self) -> PyConditions {
        PyConditions {
            inner: self.inner.conditions.clone(),
        }
    }

    /// Serialize this Recipe to a JSON string.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| PyValueError::new_err(format!("serde error: {e}")))
    }

    /// Deserialize a Recipe from a JSON string.
    #[staticmethod]
    fn from_json(json: &str) -> PyResult<Self> {
        serde_json::from_str(json)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(format!("serde error: {e}")))
    }
}

/// PyO3 wrapper for [`crate::ontology::recipe::StateVector`] (v7.6).
///
/// NOTE: This is a DIFFERENT class from [`PyCognitiveStateVector`], which
/// exposes the v7.4/v7.5 open-simplex state vector. The v7.6 state vector
/// records available quantities of CAS primitives for yield analysis — no
/// normalization constraint.
#[pyclass(name = "ProductionStateVector")]
#[derive(Clone)]
pub struct PyProductionStateVector {
    inner: recipe_mod::StateVector,
}

#[pymethods]
impl PyProductionStateVector {
    /// Construct an empty state vector. Add activations with `set`.
    #[new]
    fn new() -> Self {
        Self {
            inner: recipe_mod::StateVector::empty(),
        }
    }

    /// Record an available quantity for a primitive.
    fn set(&mut self, primitive: &PyPrimitiveId, quantity: f64) {
        self.inner.set(primitive.inner, quantity);
    }

    /// Look up the quantity for a primitive; missing entries return 0.
    fn quantity(&self, primitive: &PyPrimitiveId) -> f64 {
        self.inner.quantity(&primitive.inner)
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

/// PyO3 wrapper for [`crate::scoring::yield_calc::Yield`].
#[pyclass(name = "Yield")]
#[derive(Clone)]
pub struct PyYield {
    inner: yield_mod::Yield,
}

#[pymethods]
impl PyYield {
    #[getter]
    fn theoretical(&self) -> f64 {
        self.inner.theoretical
    }

    #[getter]
    fn actual(&self) -> Option<f64> {
        self.inner.actual
    }

    #[getter]
    fn efficiency(&self) -> Option<f64> {
        self.inner.efficiency
    }

    /// Construct a full Yield with an actual measurement; efficiency is
    /// computed via [`crate::scoring::yield_calc::efficiency`].
    #[staticmethod]
    fn with_actual(theoretical: f64, actual: f64) -> Self {
        Self {
            inner: yield_mod::Yield::with_actual(theoretical, actual),
        }
    }
}

/// PyO3 wrapper for [`crate::scoring::yield_calc::LimitingReagent`].
///
/// The variant name is exposed via the `kind` getter
/// (`"primitive"` / `"multiple"` / `"none"`); callers inspect `primitive`,
/// `primitives`, `ratio`, or `ratios` depending on kind.
#[pyclass(name = "LimitingReagent")]
#[derive(Clone)]
pub struct PyLimitingReagent {
    inner: yield_mod::LimitingReagent,
}

#[pymethods]
impl PyLimitingReagent {
    #[getter]
    fn kind(&self) -> &'static str {
        match &self.inner {
            yield_mod::LimitingReagent::Primitive(_, _) => "primitive",
            yield_mod::LimitingReagent::Multiple(_) => "multiple",
            yield_mod::LimitingReagent::None => "none",
        }
    }

    /// For `kind = "primitive"`, the sole limiting primitive. Else `None`.
    fn primitive(&self) -> Option<PyPrimitiveId> {
        match &self.inner {
            yield_mod::LimitingReagent::Primitive(p, _) => Some(PyPrimitiveId { inner: *p }),
            _ => None,
        }
    }

    /// For `kind = "primitive"`, the ratio `xᵢ / aᵢ`. Else `None`.
    fn ratio(&self) -> Option<f64> {
        match &self.inner {
            yield_mod::LimitingReagent::Primitive(_, r) => Some(*r),
            _ => None,
        }
    }

    /// For `kind = "multiple"`, the list of `(PrimitiveId, ratio)` tied at
    /// the minimum. For other kinds, an empty list.
    fn tied(&self) -> Vec<(PyPrimitiveId, f64)> {
        match &self.inner {
            yield_mod::LimitingReagent::Multiple(v) => v
                .iter()
                .map(|(p, r)| (PyPrimitiveId { inner: *p }, *r))
                .collect(),
            _ => Vec::new(),
        }
    }
}

/// Compute `Y_T = min_i(xᵢ / aᵢ)` per Clarification 9 Section 2.
#[pyfunction]
fn theoretical_yield(recipe: &PyRecipe, state: &PyProductionStateVector) -> PyYield {
    PyYield {
        inner: yield_mod::theoretical_yield(&recipe.inner, &state.inner),
    }
}

/// Identify the limiting reagent (or tied limiting reagents) per
/// Clarification 9 Section 2.
#[pyfunction]
fn limiting_reagent(recipe: &PyRecipe, state: &PyProductionStateVector) -> PyLimitingReagent {
    PyLimitingReagent {
        inner: yield_mod::limiting_reagent(&recipe.inner, &state.inner),
    }
}

/// Compute `εᵢ = xᵢ - (Y_T · aᵢ)` for each prerequisite with `aᵢ > 0`.
/// Returns a dict keyed by canonical notation of each primitive.
#[pyfunction]
fn excess_capacity(
    recipe: &PyRecipe,
    state: &PyProductionStateVector,
) -> HashMap<String, f64> {
    let map = yield_mod::excess_capacity(&recipe.inner, &state.inner);
    let mut out: HashMap<String, f64> = HashMap::new();
    for (primitive, epsilon) in map {
        out.insert(primitive.canonical_notation(), epsilon);
    }
    out
}

/// Compute efficiency `η = actual / theoretical`. Returns NaN when
/// `theoretical <= 0.0` per module-level convention.
#[pyfunction]
fn efficiency(theoretical: f64, actual: f64) -> f64 {
    yield_mod::efficiency(theoretical, actual)
}

// ---------------------------------------------------------------------------
// CAS v7.7 Register Multiplicity bindings (Clarification 10)
// ---------------------------------------------------------------------------
//
// Exposes RegisterSet (|⟨…⟩ notation), NamedEmergentRegister (emergent fused
// cross-register result), and Rule 4 admissibility validator. All are
// additive over v7.5/v7.6 — no existing type is modified.

/// PyO3 wrapper for [`crate::ontology::RegisterSet`].
///
/// A non-empty ordered set of Phenomenological Registers, canonical CAS
/// notation `|⟨R1,R2,…⟩`. Per Clarification 10 Section 2A, this notation
/// denotes architectural specification — state presence in these registers
/// without any claim about interaction dynamics.
#[pyclass(name = "RegisterSet", eq, hash, frozen)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyRegisterSet {
    inner: ontology::RegisterSet,
}

#[pymethods]
impl PyRegisterSet {
    /// Construct a `RegisterSet` from a list of register symbol strings.
    /// Duplicates are silently deduplicated; an empty list is rejected.
    /// Accepts the canonical short forms "T", "A", "f" (lowercase
    /// authoritative per Clarification 8 Section 3), and "E".
    #[new]
    fn new(symbols: Vec<String>) -> PyResult<Self> {
        let mut registers: Vec<ontology::Register> = Vec::with_capacity(symbols.len());
        for s in &symbols {
            let r = ontology::Register::from_symbol(s).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "register symbol must be one of 'T', 'A', 'f', 'E'; got {s:?}"
                ))
            })?;
            registers.push(r);
        }
        ontology::RegisterSet::from_registers(&registers)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    /// Membership test: is the given register symbol present?
    fn contains(&self, symbol: &str) -> PyResult<bool> {
        let r = ontology::Register::from_symbol(symbol).ok_or_else(|| {
            PyValueError::new_err(format!(
                "register symbol must be one of 'T', 'A', 'f', 'E'; got {symbol:?}"
            ))
        })?;
        Ok(self.inner.contains(&r))
    }

    /// Subset test: `self ⊆ other`.
    fn is_subset_of(&self, other: &PyRegisterSet) -> bool {
        self.inner.is_subset_of(&other.inner)
    }

    /// Superset test: `self ⊇ other`.
    fn is_superset_of(&self, other: &PyRegisterSet) -> bool {
        self.inner.is_superset_of(&other.inner)
    }

    /// Whether the set contains both members of a register involution pair
    /// ({|T, |E} or {|A, |f}) per Clarification 8 Section 3.
    fn involution_pair_present(&self) -> bool {
        self.inner.involution_pair_present()
    }

    /// Canonical CAS notation WITHOUT the `|` prefix, e.g. `"⟨T,A,f⟩"`.
    #[getter]
    fn canonical_notation(&self) -> String {
        self.inner.canonical_notation()
    }

    /// Cardinality of the set.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// List the contained registers as short-form symbols in canonical
    /// order ("T", "A", "f", "E").
    fn symbols(&self) -> Vec<&'static str> {
        self.inner.iter().map(|r| r.symbol()).collect()
    }

    fn __repr__(&self) -> String {
        format!("RegisterSet({})", self.inner.canonical_notation())
    }

    fn __str__(&self) -> String {
        self.inner.canonical_notation()
    }

    /// Serialize to a JSON string — the v7.5-compatible array-of-symbols
    /// form, e.g. `["T","A","f"]`.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| PyValueError::new_err(format!("serde error: {e}")))
    }

    /// Deserialize from a JSON string.
    #[staticmethod]
    fn from_json(json: &str) -> PyResult<Self> {
        serde_json::from_str(json)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(format!("serde error: {e}")))
    }
}

/// PyO3 wrapper for [`crate::ontology::NamedEmergentRegister`].
///
/// A named identifier (e.g., "Ω", "TF") for the unified emergent result of
/// a same-Noetic cross-register `×` integration per Clarification 10
/// Section 2C.
#[pyclass(name = "NamedEmergentRegister", eq, hash, frozen)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyNamedEmergentRegister {
    inner: ontology::NamedEmergentRegister,
}

#[pymethods]
impl PyNamedEmergentRegister {
    /// Construct from a name string. Validates: non-empty, starts with ASCII
    /// letter or Greek uppercase, subsequent chars ASCII letter/digit/
    /// underscore.
    #[new]
    fn new(name: &str) -> PyResult<Self> {
        ontology::NamedEmergentRegister::from_str(name)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(format!("{e}")))
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }

    fn __repr__(&self) -> String {
        format!("NamedEmergentRegister({})", self.inner.name)
    }

    fn __str__(&self) -> String {
        self.inner.name.clone()
    }
}

/// PyO3 wrapper for the Rule 4 validator result enum.
///
/// The variant is exposed via `.kind` (`"valid"` or
/// `"violation_requires_emergent_result"`). For the violation variant,
/// `.violation_registers()` returns the distinct register symbols and
/// `.violation_core()` returns a `(operator_index, domain_index_or_-1,
/// drive_number_or_0)` triple describing the shared core.
#[pyclass(name = "RuleFourResult")]
#[derive(Clone)]
pub struct PyRuleFourResult {
    inner: validation::RuleFourResult,
}

#[pymethods]
impl PyRuleFourResult {
    #[getter]
    fn kind(&self) -> &'static str {
        match &self.inner {
            validation::RuleFourResult::Valid => "valid",
            validation::RuleFourResult::ViolationRequiresEmergentResult { .. } => {
                "violation_requires_emergent_result"
            }
        }
    }

    /// For the violation variant, return the distinct register symbols
    /// that triggered the violation. Empty list for the valid variant.
    fn violation_registers(&self) -> Vec<&'static str> {
        match &self.inner {
            validation::RuleFourResult::ViolationRequiresEmergentResult { registers, .. } => {
                registers.iter().map(|r| r.symbol()).collect()
            }
            _ => Vec::new(),
        }
    }

    /// For the violation variant, return the shared
    /// `(operator_index, domain_index_or_-1, drive_number_or_0)` core.
    /// Returns `None` for the valid variant. `domain_index` is `-1` when
    /// the core had no domain; `drive_number` is `0` when the core had no
    /// drive.
    fn violation_core(&self) -> Option<(usize, i32, u8)> {
        match &self.inner {
            validation::RuleFourResult::ViolationRequiresEmergentResult { core, .. } => {
                let op_idx = core.noetic.index();
                let dom_idx = core.domain.map(|d| d.index() as i32).unwrap_or(-1);
                let drv_num = core.drive.map(|d| d.number()).unwrap_or(0);
                Some((op_idx, dom_idx, drv_num))
            }
            _ => None,
        }
    }

    fn __repr__(&self) -> String {
        match &self.inner {
            validation::RuleFourResult::Valid => "RuleFourResult(valid)".to_string(),
            validation::RuleFourResult::ViolationRequiresEmergentResult {
                registers, ..
            } => {
                let regs: Vec<&'static str> = registers.iter().map(|r| r.symbol()).collect();
                format!(
                    "RuleFourResult(violation_requires_emergent_result, registers={regs:?})"
                )
            }
        }
    }
}

/// Validate a list of `×`-cross-product operands against Clarification 10
/// Section 4 (Rule 4). Each operand is encoded as a tuple
/// `(operator_index, domain_index_or_None, drive_number_or_None,
/// register_symbol_or_None)`. `named_emergent_result` is an optional
/// [`PyNamedEmergentRegister`] or name string identifying a named fused
/// emergent result.
#[pyfunction]
#[pyo3(signature = (operands, named_emergent_result=None))]
fn validate_same_noetic_cross_product(
    operands: Vec<(usize, Option<usize>, Option<u8>, Option<String>)>,
    named_emergent_result: Option<PyNamedEmergentRegister>,
) -> PyResult<PyRuleFourResult> {
    let mut parsed: Vec<validation::CognitiveStateWithRegister> =
        Vec::with_capacity(operands.len());
    for (op_idx, dom_idx, drv_num, reg_sym) in operands {
        let noetic = ontology::CognitiveOperator::from_index(op_idx).ok_or_else(|| {
            PyValueError::new_err(format!("operator index must be 0-9, got {op_idx}"))
        })?;
        let domain = match dom_idx {
            None => None,
            Some(idx) => Some(ontology::Domain::from_index(idx).ok_or_else(|| {
                PyValueError::new_err(format!("domain index must be 0-3, got {idx}"))
            })?),
        };
        let drive = match drv_num {
            None => None,
            Some(n) => Some(ontology::CoreDrive::from_number(n).ok_or_else(|| {
                PyValueError::new_err(format!("drive number must be 1-7, got {n}"))
            })?),
        };
        let register = match reg_sym.as_deref() {
            None => None,
            Some(s) => Some(ontology::Register::from_symbol(s).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "register symbol must be one of 'T', 'A', 'f', 'E'; got {s:?}"
                ))
            })?),
        };
        parsed.push(validation::CognitiveStateWithRegister::new(
            noetic, domain, drive, register,
        ));
    }
    let named = named_emergent_result.as_ref().map(|n| &n.inner);
    let result = validation::validate_same_noetic_cross_product(&parsed, named);
    Ok(PyRuleFourResult { inner: result })
}

// ---------------------------------------------------------------------------
// CAS-Native v2 ADR-06 batch APIs
// ---------------------------------------------------------------------------
//
// Batch wrappers exposed for the CAS-Native v2 Rust bridge (ADR-06). Each
// batch PyO3 entry point parses a list of per-sample inputs, delegates to
// the existing per-sample Rust function via the public batch wrapper, and
// returns a list of result objects. Ordering is preserved.

/// Parse a single Rule 4 operand encoded as
/// `(operator_index, domain_index_or_None, drive_number_or_None,
/// register_symbol_or_None)` into a [`validation::CognitiveStateWithRegister`].
fn parse_operand_tuple(
    op_idx: usize,
    dom_idx: Option<usize>,
    drv_num: Option<u8>,
    reg_sym: Option<String>,
) -> PyResult<validation::CognitiveStateWithRegister> {
    let noetic = ontology::CognitiveOperator::from_index(op_idx).ok_or_else(|| {
        PyValueError::new_err(format!("operator index must be 0-9, got {op_idx}"))
    })?;
    let domain = match dom_idx {
        None => None,
        Some(idx) => Some(ontology::Domain::from_index(idx).ok_or_else(|| {
            PyValueError::new_err(format!("domain index must be 0-3, got {idx}"))
        })?),
    };
    let drive = match drv_num {
        None => None,
        Some(n) => Some(ontology::CoreDrive::from_number(n).ok_or_else(|| {
            PyValueError::new_err(format!("drive number must be 1-7, got {n}"))
        })?),
    };
    let register = match reg_sym.as_deref() {
        None => None,
        Some(s) => Some(ontology::Register::from_symbol(s).ok_or_else(|| {
            PyValueError::new_err(format!(
                "register symbol must be one of 'T', 'A', 'f', 'E'; got {s:?}"
            ))
        })?),
    };
    Ok(validation::CognitiveStateWithRegister::new(
        noetic, domain, drive, register,
    ))
}

/// ADR-06 batch validator for Rule 4.
///
/// Each batch element is a tuple `(operands, named_emergent_result)` where
/// `operands` is a list of operand tuples (see
/// [`validate_same_noetic_cross_product`] above for the tuple layout) and
/// `named_emergent_result` is an optional [`PyNamedEmergentRegister`]. Returns
/// a list of [`PyRuleFourResult`] in the same order as the input.
#[pyfunction(name = "validate_same_noetic_cross_product_batch")]
fn py_validate_same_noetic_cross_product_batch(
    expressions: Vec<(
        Vec<(usize, Option<usize>, Option<u8>, Option<String>)>,
        Option<PyNamedEmergentRegister>,
    )>,
) -> PyResult<Vec<PyRuleFourResult>> {
    let mut parsed: Vec<validation::RuleFourBatchInput> = Vec::with_capacity(expressions.len());
    for (operand_tuples, named_py) in expressions {
        let mut operands: Vec<validation::CognitiveStateWithRegister> =
            Vec::with_capacity(operand_tuples.len());
        for (op_idx, dom_idx, drv_num, reg_sym) in operand_tuples {
            operands.push(parse_operand_tuple(op_idx, dom_idx, drv_num, reg_sym)?);
        }
        let named = named_py.map(|n| n.inner);
        parsed.push((operands, named));
    }
    let results = validation::validate_same_noetic_cross_product_batch(&parsed);
    Ok(results
        .into_iter()
        .map(|inner| PyRuleFourResult { inner })
        .collect())
}

/// PyO3 wrapper for [`ontology::ValidationResult`]. Fields surface the
/// discriminant (`kind`), optional `reason` tag, and optional `detail`
/// message so Python callers can dispatch on the tag without textual parsing.
#[pyclass(name = "ValidationResult")]
#[derive(Clone)]
pub struct PyValidationResult {
    inner: ontology::ValidationResult,
}

#[pymethods]
impl PyValidationResult {
    #[getter]
    fn kind(&self) -> &'static str {
        match &self.inner {
            ontology::ValidationResult::Valid => "valid",
            ontology::ValidationResult::Invalid { .. } => "invalid",
        }
    }

    /// Machine-readable reason tag (e.g., `"empty_register_set"`). `None`
    /// for the valid variant.
    #[getter]
    fn reason(&self) -> Option<String> {
        match &self.inner {
            ontology::ValidationResult::Invalid { reason, .. } => Some(reason.clone()),
            _ => None,
        }
    }

    /// Human-readable detail string. `None` for the valid variant.
    #[getter]
    fn detail(&self) -> Option<String> {
        match &self.inner {
            ontology::ValidationResult::Invalid { detail, .. } => Some(detail.clone()),
            _ => None,
        }
    }

    fn is_valid(&self) -> bool {
        self.inner.is_valid()
    }

    fn __repr__(&self) -> String {
        match &self.inner {
            ontology::ValidationResult::Valid => "ValidationResult(valid)".to_string(),
            ontology::ValidationResult::Invalid { reason, .. } => {
                format!("ValidationResult(invalid, reason={reason:?})")
            }
        }
    }
}

/// ADR-06 batch verification for `(RegisterSet, NamedEmergentRegister)` pairs.
///
/// Each element of `inputs` is a `(register_set, named_emergent_register)`
/// pair. Returns a list of [`PyValidationResult`] preserving order.
#[pyfunction(name = "verify_named_emergent_register_batch")]
fn py_verify_named_emergent_register_batch(
    inputs: Vec<(PyRegisterSet, PyNamedEmergentRegister)>,
) -> Vec<PyValidationResult> {
    let parsed: Vec<ontology::NamedEmergentBatchInput> = inputs
        .into_iter()
        .map(|(rs, ner)| (rs.inner, ner.inner))
        .collect();
    ontology::verify_named_emergent_register_batch(&parsed)
        .into_iter()
        .map(|inner| PyValidationResult { inner })
        .collect()
}

/// PyO3 wrapper for [`yield_mod::YieldResult`]. Exposes the theoretical
/// yield, a [`PyLimitingReagent`], optional actual yield, optional
/// efficiency, and the excess-capacity map keyed by primitive canonical
/// notation.
#[pyclass(name = "YieldResult")]
#[derive(Clone)]
pub struct PyYieldResult {
    inner: yield_mod::YieldResult,
}

#[pymethods]
impl PyYieldResult {
    #[getter]
    fn theoretical_yield(&self) -> f64 {
        self.inner.theoretical_yield
    }

    #[getter]
    fn limiting_reagent(&self) -> PyLimitingReagent {
        PyLimitingReagent {
            inner: self.inner.limiting_reagent.clone(),
        }
    }

    #[getter]
    fn actual_yield(&self) -> Option<f64> {
        self.inner.actual_yield
    }

    #[getter]
    fn efficiency(&self) -> Option<f64> {
        self.inner.efficiency
    }

    /// Excess capacity per prerequisite, keyed by canonical notation string.
    #[getter]
    fn excess_capacity(&self) -> HashMap<String, f64> {
        self.inner
            .excess_capacity
            .iter()
            .map(|(p, e)| (p.canonical_notation(), *e))
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "YieldResult(Y_T={:.6}, actual={:?}, η={:?})",
            self.inner.theoretical_yield, self.inner.actual_yield, self.inner.efficiency
        )
    }
}

/// ADR-06 batch yield computation.
///
/// Each element of `inputs` is a `(recipe, state, observed_yield_or_None)`
/// triple. Returns a list of [`PyYieldResult`] preserving order.
#[pyfunction(name = "compute_yield_batch")]
fn py_compute_yield_batch(
    inputs: Vec<(PyRecipe, PyProductionStateVector, Option<f64>)>,
) -> Vec<PyYieldResult> {
    let parsed: Vec<yield_mod::YieldBatchInput> = inputs
        .into_iter()
        .map(|(r, s, o)| (r.inner, s.inner, o))
        .collect();
    yield_mod::compute_yield_batch(&parsed)
        .into_iter()
        .map(|inner| PyYieldResult { inner })
        .collect()
}

// ---------------------------------------------------------------------------
// Module registration
// ---------------------------------------------------------------------------

#[pymodule]
pub fn cas_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCognitiveOperator>()?;
    m.add_class::<PyDomain>()?;
    m.add_class::<PyCoreDrive>()?;
    m.add_class::<PyRegister>()?;
    m.add_class::<PyCognitiveStateVector>()?;
    m.add_class::<PyDialConfig>()?;
    m.add_class::<PyOperatorScores>()?;
    m.add_class::<PyDomainCoherence>()?;
    m.add_class::<PyInversionScanner>()?;
    m.add_class::<PyRpmProfile>()?;
    // CAS v7.6 production semantics
    m.add_class::<PyPrimitiveId>()?;
    m.add_class::<PyProductionTarget>()?;
    m.add_class::<PyLeakage>()?;
    m.add_class::<PyCatalyst>()?;
    m.add_class::<PyInhibitor>()?;
    m.add_class::<PyConditions>()?;
    m.add_class::<PyRecipe>()?;
    m.add_class::<PyProductionStateVector>()?;
    m.add_class::<PyYield>()?;
    m.add_class::<PyLimitingReagent>()?;
    // CAS v7.7 Register Multiplicity (Clarification 10)
    m.add_class::<PyRegisterSet>()?;
    m.add_class::<PyNamedEmergentRegister>()?;
    m.add_class::<PyRuleFourResult>()?;
    // CAS-Native v2 ADR-06 batch API result types
    m.add_class::<PyValidationResult>()?;
    m.add_class::<PyYieldResult>()?;
    m.add_function(wrap_pyfunction!(compute_nccs, m)?)?;
    m.add_function(wrap_pyfunction!(geodesic_distance, m)?)?;
    m.add_function(wrap_pyfunction!(bhattacharyya_coefficient, m)?)?;
    m.add_function(wrap_pyfunction!(multiply_state_vectors, m)?)?;
    m.add_function(wrap_pyfunction!(divide_state_vectors, m)?)?;
    m.add_function(wrap_pyfunction!(multiply_cognitive_states, m)?)?;
    m.add_function(wrap_pyfunction!(divide_cognitive_states, m)?)?;
    m.add_function(wrap_pyfunction!(synthesize_drives, m)?)?;
    // CAS v7.6 production-semantics algorithms
    m.add_function(wrap_pyfunction!(theoretical_yield, m)?)?;
    m.add_function(wrap_pyfunction!(limiting_reagent, m)?)?;
    m.add_function(wrap_pyfunction!(excess_capacity, m)?)?;
    m.add_function(wrap_pyfunction!(efficiency, m)?)?;
    // CAS v7.7 Rule 4 admissibility validator (Clarification 10)
    m.add_function(wrap_pyfunction!(validate_same_noetic_cross_product, m)?)?;
    // CAS-Native v2 ADR-06 batch APIs (Rust engine alignment)
    m.add_function(wrap_pyfunction!(py_validate_same_noetic_cross_product_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_verify_named_emergent_register_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_yield_batch, m)?)?;
    Ok(())
}
