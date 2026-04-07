//! Processing Domains: P (Principled), C (Cognitive), E (Evaluative), O (Operational)
//!
//! Total order: P > C > E > O
//! Domain Descent: P -> C -> E -> O (causation); O -> P (feedback)

use serde::{Deserialize, Serialize};
use std::fmt;

/// The four processing domains in the CAS framework.
/// Ordered: Principled > Cognitive > Evaluative > Operational.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Domain {
    Principled = 0,
    Cognitive = 1,
    Evaluative = 2,
    Operational = 3,
}

impl Domain {
    /// All domains in descending precedence order.
    pub const ALL: [Domain; 4] = [
        Self::Principled,
        Self::Cognitive,
        Self::Evaluative,
        Self::Operational,
    ];

    /// Index (0-3) corresponding to precedence rank (0 = highest).
    pub fn index(self) -> usize {
        self as usize
    }

    /// Construct from index. Returns None if out of range.
    pub fn from_index(idx: usize) -> Option<Self> {
        match idx {
            0 => Some(Self::Principled),
            1 => Some(Self::Cognitive),
            2 => Some(Self::Evaluative),
            3 => Some(Self::Operational),
            _ => None,
        }
    }

    /// Single-letter abbreviation.
    pub fn abbreviation(self) -> char {
        match self {
            Self::Principled => 'P',
            Self::Cognitive => 'C',
            Self::Evaluative => 'E',
            Self::Operational => 'O',
        }
    }

    /// Whether self has higher precedence than other (P > C > E > O).
    pub fn dominates(self, other: Self) -> bool {
        (self as u8) < (other as u8)
    }

    /// The next domain in the descent chain (P->C->E->O).
    /// Returns None for Operational (terminal in the descent).
    pub fn descend(self) -> Option<Self> {
        match self {
            Self::Principled => Some(Self::Cognitive),
            Self::Cognitive => Some(Self::Evaluative),
            Self::Evaluative => Some(Self::Operational),
            Self::Operational => None,
        }
    }

    /// Feedback loop: O -> P. Returns Some(Principled) only for Operational.
    pub fn feedback(self) -> Option<Self> {
        match self {
            Self::Operational => Some(Self::Principled),
            _ => None,
        }
    }
}

impl fmt::Display for Domain {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Principled => write!(f, "Principled"),
            Self::Cognitive => write!(f, "Cognitive"),
            Self::Evaluative => write!(f, "Evaluative"),
            Self::Operational => write!(f, "Operational"),
        }
    }
}

impl PartialOrd for Domain {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

/// Total order: P > C > E > O. Lower index = higher precedence.
impl Ord for Domain {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        // Reverse because lower index = higher precedence
        (*other as u8).cmp(&(*self as u8))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_total_order() {
        assert!(Domain::Principled > Domain::Cognitive);
        assert!(Domain::Cognitive > Domain::Evaluative);
        assert!(Domain::Evaluative > Domain::Operational);
    }

    #[test]
    fn test_dominates() {
        assert!(Domain::Principled.dominates(Domain::Cognitive));
        assert!(Domain::Principled.dominates(Domain::Operational));
        assert!(!Domain::Operational.dominates(Domain::Principled));
        assert!(!Domain::Cognitive.dominates(Domain::Cognitive));
    }

    #[test]
    fn test_descent_chain() {
        assert_eq!(Domain::Principled.descend(), Some(Domain::Cognitive));
        assert_eq!(Domain::Cognitive.descend(), Some(Domain::Evaluative));
        assert_eq!(Domain::Evaluative.descend(), Some(Domain::Operational));
        assert_eq!(Domain::Operational.descend(), None);
    }

    #[test]
    fn test_feedback() {
        assert_eq!(Domain::Operational.feedback(), Some(Domain::Principled));
        assert_eq!(Domain::Principled.feedback(), None);
        assert_eq!(Domain::Cognitive.feedback(), None);
    }

    #[test]
    fn test_from_index_roundtrip() {
        for d in Domain::ALL {
            assert_eq!(Domain::from_index(d.index()), Some(d));
        }
        assert_eq!(Domain::from_index(4), None);
    }

    #[test]
    fn test_abbreviations() {
        assert_eq!(Domain::Principled.abbreviation(), 'P');
        assert_eq!(Domain::Cognitive.abbreviation(), 'C');
        assert_eq!(Domain::Evaluative.abbreviation(), 'E');
        assert_eq!(Domain::Operational.abbreviation(), 'O');
    }
}
