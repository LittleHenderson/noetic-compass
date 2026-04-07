//! Core Drives (F1-F7) and Domain-Specific Drives (28 total)
//!
//! 7 Core Drives: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose
//! Drive inversion pairs: F1<->F7, F2<->F6, F3<->F5. F4 is self-dual.
//! 28 Domain-Specific Drives: 7 drives x 4 domains.

use serde::{Deserialize, Serialize};
use std::fmt;

use super::domains::Domain;

/// The 7 core drives in the CAS framework.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum CoreDrive {
    F1Unity = 1,
    F2Wisdom = 2,
    F3Vitality = 3,
    F4Connection = 4,
    F5Agency = 5,
    F6Structure = 6,
    F7Purpose = 7,
}

impl CoreDrive {
    /// All drives in order.
    pub const ALL: [CoreDrive; 7] = [
        Self::F1Unity,
        Self::F2Wisdom,
        Self::F3Vitality,
        Self::F4Connection,
        Self::F5Agency,
        Self::F6Structure,
        Self::F7Purpose,
    ];

    /// The three inversion pairs.
    pub const INVERSION_PAIRS: [(CoreDrive, CoreDrive); 3] = [
        (Self::F1Unity, Self::F7Purpose),
        (Self::F2Wisdom, Self::F6Structure),
        (Self::F3Vitality, Self::F5Agency),
    ];

    /// The self-dual drive.
    pub const SELF_DUAL: CoreDrive = Self::F4Connection;

    /// 1-based index (F1=1, ..., F7=7).
    pub fn number(self) -> u8 {
        self as u8
    }

    /// 0-based index (F1=0, ..., F7=6).
    pub fn index(self) -> usize {
        (self as u8 - 1) as usize
    }

    /// Construct from 1-based number.
    pub fn from_number(n: u8) -> Option<Self> {
        match n {
            1 => Some(Self::F1Unity),
            2 => Some(Self::F2Wisdom),
            3 => Some(Self::F3Vitality),
            4 => Some(Self::F4Connection),
            5 => Some(Self::F5Agency),
            6 => Some(Self::F6Structure),
            7 => Some(Self::F7Purpose),
            _ => None,
        }
    }

    /// Returns the inversion partner (F1<->F7, F2<->F6, F3<->F5, F4=F4).
    pub fn invert(self) -> Self {
        match self {
            Self::F1Unity => Self::F7Purpose,
            Self::F2Wisdom => Self::F6Structure,
            Self::F3Vitality => Self::F5Agency,
            Self::F4Connection => Self::F4Connection,
            Self::F5Agency => Self::F3Vitality,
            Self::F6Structure => Self::F2Wisdom,
            Self::F7Purpose => Self::F1Unity,
        }
    }

    /// Whether this drive is self-dual under inversion.
    pub fn is_self_dual(self) -> bool {
        self == Self::F4Connection
    }

    /// Human-readable name of the drive.
    pub fn name(self) -> &'static str {
        match self {
            Self::F1Unity => "Unity",
            Self::F2Wisdom => "Wisdom",
            Self::F3Vitality => "Vitality",
            Self::F4Connection => "Connection",
            Self::F5Agency => "Agency",
            Self::F6Structure => "Structure",
            Self::F7Purpose => "Purpose",
        }
    }
}

impl fmt::Display for CoreDrive {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "F{} {}", self.number(), self.name())
    }
}

/// A domain-specific drive: one of 28 = 7 drives x 4 domains.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct DomainDrive {
    drive: CoreDrive,
    domain: Domain,
}

impl DomainDrive {
    pub fn new(drive: CoreDrive, domain: Domain) -> Self {
        Self { drive, domain }
    }

    pub fn drive(self) -> CoreDrive {
        self.drive
    }

    pub fn domain(self) -> Domain {
        self.domain
    }

    /// Linear index in [0, 27]. Layout: drive-major (0-based), domain-minor.
    pub fn linear_index(self) -> usize {
        self.drive.index() * 4 + self.domain.index()
    }

    /// Construct from linear index [0, 27].
    pub fn from_linear_index(idx: usize) -> Option<Self> {
        if idx >= 28 {
            return None;
        }
        let drive = CoreDrive::from_number((idx / 4) as u8 + 1)?;
        let domain = Domain::from_index(idx % 4)?;
        Some(Self { drive, domain })
    }

    /// All 28 domain-specific drives.
    pub fn all() -> Vec<DomainDrive> {
        (0..28)
            .map(|i| Self::from_linear_index(i).unwrap())
            .collect()
    }
}

impl fmt::Display for DomainDrive {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "F{}-{}",
            self.drive.number(),
            self.domain.abbreviation()
        )
    }
}

/// Score for a single core drive (0.0 to 1.0).
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct DriveScore {
    drive: CoreDrive,
    score: f64,
}

impl DriveScore {
    pub fn new(drive: CoreDrive, score: f64) -> Option<Self> {
        if !(0.0..=1.0).contains(&score) || score.is_nan() {
            return None;
        }
        Some(Self { drive, score })
    }

    pub fn drive(self) -> CoreDrive {
        self.drive
    }

    pub fn score(self) -> f64 {
        self.score
    }
}

/// Complete drive profile: scores for all 7 core drives.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriveProfile {
    scores: [f64; 7],
}

impl DriveProfile {
    pub fn new(scores: [f64; 7]) -> Option<Self> {
        for &s in &scores {
            if !(0.0..=1.0).contains(&s) || s.is_nan() {
                return None;
            }
        }
        Some(Self { scores })
    }

    pub fn get(&self, drive: CoreDrive) -> f64 {
        self.scores[drive.index()]
    }

    /// Compute the inversion balance for a pair: |score(a) - score(b)|.
    pub fn inversion_balance(&self, a: CoreDrive, b: CoreDrive) -> f64 {
        (self.scores[a.index()] - self.scores[b.index()]).abs()
    }

    /// Compute all three inversion balance values.
    pub fn all_inversion_balances(&self) -> [f64; 3] {
        CoreDrive::INVERSION_PAIRS.map(|(a, b)| self.inversion_balance(a, b))
    }

    /// Average score across all 7 drives.
    pub fn average(&self) -> f64 {
        self.scores.iter().sum::<f64>() / 7.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drive_inversion_is_involution() {
        for d in CoreDrive::ALL {
            assert_eq!(d.invert().invert(), d);
        }
    }

    #[test]
    fn test_drive_inversion_pairs() {
        assert_eq!(CoreDrive::F1Unity.invert(), CoreDrive::F7Purpose);
        assert_eq!(CoreDrive::F2Wisdom.invert(), CoreDrive::F6Structure);
        assert_eq!(CoreDrive::F3Vitality.invert(), CoreDrive::F5Agency);
        assert_eq!(CoreDrive::F4Connection.invert(), CoreDrive::F4Connection);
    }

    #[test]
    fn test_self_dual() {
        assert!(CoreDrive::F4Connection.is_self_dual());
        for d in CoreDrive::ALL {
            if d != CoreDrive::F4Connection {
                assert!(!d.is_self_dual());
            }
        }
    }

    #[test]
    fn test_domain_drive_count() {
        assert_eq!(DomainDrive::all().len(), 28);
    }

    #[test]
    fn test_domain_drive_linear_index_roundtrip() {
        for i in 0..28 {
            let dd = DomainDrive::from_linear_index(i).unwrap();
            assert_eq!(dd.linear_index(), i);
        }
        assert!(DomainDrive::from_linear_index(28).is_none());
    }

    #[test]
    fn test_drive_score_bounds() {
        assert!(DriveScore::new(CoreDrive::F1Unity, -0.1).is_none());
        assert!(DriveScore::new(CoreDrive::F1Unity, 1.1).is_none());
        assert!(DriveScore::new(CoreDrive::F1Unity, 0.5).is_some());
        assert!(DriveScore::new(CoreDrive::F1Unity, f64::NAN).is_none());
    }

    #[test]
    fn test_drive_profile_inversion_balance() {
        let profile = DriveProfile::new([0.8, 0.6, 0.7, 0.5, 0.3, 0.4, 0.2]).unwrap();
        // F1(0.8) <-> F7(0.2) => balance = 0.6
        assert!((profile.inversion_balance(CoreDrive::F1Unity, CoreDrive::F7Purpose) - 0.6).abs() < 1e-12);
        // F2(0.6) <-> F6(0.4) => balance = 0.2
        assert!((profile.inversion_balance(CoreDrive::F2Wisdom, CoreDrive::F6Structure) - 0.2).abs() < 1e-12);
    }
}
