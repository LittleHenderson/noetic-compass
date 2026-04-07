//! PyO3 bindings for the CAS Scoring Engine.
//!
//! Exposes the core CAS types and scoring functions to Python via maturin.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyIndexError};
use std::collections::HashMap;

use crate::ontology;
use crate::scoring;
use crate::metric;
use crate::inversions;
use crate::rpm;

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
            .ok_or_else(|| PyValueError::new_err(format!("operator index must be 0-9, got {index}")))
    }

    #[getter]
    fn index(&self) -> usize {
        self.inner.index()
    }

    fn involute(&self) -> Self {
        Self { inner: self.inner.involute() }
    }

    fn is_self_dual(&self) -> bool {
        self.inner.is_self_dual()
    }

    fn compose(&self, other: &PyCognitiveOperator) -> Self {
        Self { inner: self.inner.compose(other.inner) }
    }

    fn is_admissible(&self, source_index: usize, target_index: usize) -> PyResult<bool> {
        let src = ontology::CognitiveStateId::from_linear_index(source_index)
            .ok_or_else(|| PyValueError::new_err(format!("source index must be 0-39, got {source_index}")))?;
        let tgt = ontology::CognitiveStateId::from_linear_index(target_index)
            .ok_or_else(|| PyValueError::new_err(format!("target index must be 0-39, got {target_index}")))?;
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
        Self { inner: self.inner.invert() }
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
        let domain = ontology::Domain::from_index(domain_index)
            .ok_or_else(|| PyValueError::new_err(format!("domain index must be 0-3, got {domain_index}")))?;
        Ok(self.inner.domain_average(domain))
    }

    fn as_list(&self) -> Vec<f64> {
        self.inner.as_slice().to_vec()
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
        let op = ontology::CognitiveOperator::from_index(operator_index)
            .ok_or_else(|| PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}")))?;
        Ok(self.inner.get(op).value())
    }

    fn set(&mut self, operator_index: usize, value: u8) -> PyResult<()> {
        let op = ontology::CognitiveOperator::from_index(operator_index)
            .ok_or_else(|| PyValueError::new_err(format!("operator index must be 0-9, got {operator_index}")))?;
        self.inner.set(op, value).map_err(|e| PyValueError::new_err(format!("{e}")))
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
                return Err(PyValueError::new_err("domain_drive_scores must have 7 rows"));
            }
            let mut arr = [[0.5f64; 4]; 7];
            for (i, row) in dds_vec.iter().enumerate() {
                if row.len() != 4 {
                    return Err(PyValueError::new_err("each domain_drive_scores row must have 4 values"));
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
                    return Err(PyValueError::new_err("each pathway_scores row must have 4 values"));
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
        let result = scanner.scan(&input)
            .map_err(|e| PyValueError::new_err(format!("{e}")))?;

        Python::with_gil(|py| {
            let mut map: HashMap<String, PyObject> = HashMap::new();

            let axis_scores: Vec<f64> = result.axis_scores().to_vec();
            map.insert("axis_scores".to_string(), axis_scores.into_pyobject(py)?.into());
            map.insert("stealth_resistance".to_string(), result.stealth_resistance().into_pyobject(py)?.into());
            map.insert("compound_severity".to_string(), result.compound_severity().into_pyobject(py)?.into());

            let resistance_input = result.to_resistance_input();
            map.insert("resistance_score".to_string(), resistance_input.resistance_score().into_pyobject(py)?.into());

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
        let drive = ontology::CoreDrive::from_number(drive_number)
            .ok_or_else(|| PyValueError::new_err(format!("drive number must be 1-7, got {drive_number}")))?;
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
    let op = scoring::OperatorScores::new(op_arr)
        .map_err(|e| PyValueError::new_err(format!("{e}")))?;

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

    let se = scoring::SocialEngineeringInput::new(manipulation_resistance, overton_drift_resistance)
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
        map.insert("operator_profile".to_string(), result.operator_profile.into_pyobject(py)?.into());
        map.insert("domain_coherence".to_string(), result.domain_coherence.into_pyobject(py)?.into());
        map.insert("drive_rpm_integrity".to_string(), result.drive_rpm_integrity.into_pyobject(py)?.into());
        map.insert("pathway_quality".to_string(), result.pathway_quality.into_pyobject(py)?.into());
        map.insert("inversion_resistance".to_string(), result.inversion_resistance.into_pyobject(py)?.into());
        map.insert("social_engineering".to_string(), result.social_engineering.into_pyobject(py)?.into());
        map.insert("composite".to_string(), result.composite.into_pyobject(py)?.into());
        map.insert("certification".to_string(), format!("{}", result.certification).into_pyobject(py)?.into());
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
// Module registration
// ---------------------------------------------------------------------------

#[pymodule]
pub fn cas_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCognitiveOperator>()?;
    m.add_class::<PyDomain>()?;
    m.add_class::<PyCoreDrive>()?;
    m.add_class::<PyCognitiveStateVector>()?;
    m.add_class::<PyDialConfig>()?;
    m.add_class::<PyOperatorScores>()?;
    m.add_class::<PyDomainCoherence>()?;
    m.add_class::<PyInversionScanner>()?;
    m.add_class::<PyRpmProfile>()?;
    m.add_function(wrap_pyfunction!(compute_nccs, m)?)?;
    m.add_function(wrap_pyfunction!(geodesic_distance, m)?)?;
    m.add_function(wrap_pyfunction!(bhattacharyya_coefficient, m)?)?;
    Ok(())
}
