//! CAS Ontology — Core type definitions
//!
//! All types derive from CAS v7.4 Corrected Edition and Referee-Defensible axioms A1-A7.
//!
//! Type hierarchy:
//! - 10 Cognitive Operators (CO-0..CO-9) with admissibility relations
//! - 4 Processing Domains (P, C, E, O) with total order
//! - 40 Cognitive States (10 x 4) on the open probability simplex
//! - 7 Core Drives (F1-F7) with inversion pairs
//! - 28 Domain-Specific Drives (7 x 4)
//! - 22 Capability Pathways with RPM chain structure
//! - 7 Inversion Axes

pub mod operators;
pub mod domains;
pub mod states;
pub mod drives;
pub mod pathways;

pub use operators::{CognitiveOperator, DialConfig, DialError, DialSetting};
pub use domains::Domain;
pub use states::{CognitiveStateId, CognitiveStateVector, StateVectorError, NUM_STATES, MIN_PROBABILITY};
pub use drives::{CoreDrive, DomainDrive, DriveProfile, DriveScore};
pub use pathways::{InversionAxis, PathwayNode, PathwaySatisfaction, PathwayStage};
