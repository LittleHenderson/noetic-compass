//! Capability Pathways: 22 nodes organized as RPM chains
//!
//! A0 (Pure Desire) + D1-D7 + W1-W7 + P1-P7 = 22 pathway nodes
//! RPM chain per drive n: A0 -> Dn -> Wn -> Pn -> Outcome
//!
//! The pathway structure models prerequisite-gated capability development:
//! - A0: Pure Desire (shared root)
//! - Dn: Drive-level aspiration (7 nodes, one per core drive)
//! - Wn: Will-level commitment (7 nodes)
//! - Pn: Proficiency-level mastery (7 nodes)

use serde::{Deserialize, Serialize};
use std::fmt;

use super::drives::CoreDrive;

/// The stage within an RPM chain.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PathwayStage {
    /// A0: Pure Desire — the shared root of all chains.
    Aspiration,
    /// Dn: Drive-level node for drive n.
    Drive,
    /// Wn: Will-level node for drive n.
    Will,
    /// Pn: Proficiency-level node for drive n.
    Proficiency,
}

impl PathwayStage {
    pub const ALL: [PathwayStage; 4] =
        [Self::Aspiration, Self::Drive, Self::Will, Self::Proficiency];

    /// The next stage in the RPM chain. Aspiration -> Drive -> Will -> Proficiency -> None.
    pub fn next(self) -> Option<Self> {
        match self {
            Self::Aspiration => Some(Self::Drive),
            Self::Drive => Some(Self::Will),
            Self::Will => Some(Self::Proficiency),
            Self::Proficiency => None,
        }
    }

    /// The previous stage (prerequisite).
    pub fn prev(self) -> Option<Self> {
        match self {
            Self::Aspiration => None,
            Self::Drive => Some(Self::Aspiration),
            Self::Will => Some(Self::Drive),
            Self::Proficiency => Some(Self::Will),
        }
    }
}

/// A single node in the capability pathway graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PathwayNode {
    /// A0: Pure Desire — shared root.
    A0,
    /// Drive-level aspiration for a specific core drive (D1-D7).
    D(CoreDrive),
    /// Will-level commitment for a specific core drive (W1-W7).
    W(CoreDrive),
    /// Proficiency-level mastery for a specific core drive (P1-P7).
    P(CoreDrive),
}

impl PathwayNode {
    /// Total number of pathway nodes.
    pub const COUNT: usize = 22;

    /// All 22 pathway nodes in canonical order: A0, D1..D7, W1..W7, P1..P7.
    pub fn all() -> Vec<PathwayNode> {
        let mut nodes = Vec::with_capacity(Self::COUNT);
        nodes.push(Self::A0);
        for d in CoreDrive::ALL {
            nodes.push(Self::D(d));
        }
        for d in CoreDrive::ALL {
            nodes.push(Self::W(d));
        }
        for d in CoreDrive::ALL {
            nodes.push(Self::P(d));
        }
        nodes
    }

    /// The stage this node belongs to.
    pub fn stage(self) -> PathwayStage {
        match self {
            Self::A0 => PathwayStage::Aspiration,
            Self::D(_) => PathwayStage::Drive,
            Self::W(_) => PathwayStage::Will,
            Self::P(_) => PathwayStage::Proficiency,
        }
    }

    /// The core drive this node is associated with, if any.
    pub fn drive(self) -> Option<CoreDrive> {
        match self {
            Self::A0 => None,
            Self::D(d) | Self::W(d) | Self::P(d) => Some(d),
        }
    }

    /// The RPM prerequisite for this node (what must be satisfied first).
    /// A0 has no prerequisite. Dn requires A0. Wn requires Dn. Pn requires Wn.
    pub fn prerequisite(self) -> Option<PathwayNode> {
        match self {
            Self::A0 => None,
            Self::D(_) => Some(Self::A0),
            Self::W(d) => Some(Self::D(d)),
            Self::P(d) => Some(Self::W(d)),
        }
    }

    /// The RPM chain for a given drive: [A0, Dn, Wn, Pn].
    pub fn chain(drive: CoreDrive) -> [PathwayNode; 4] {
        [Self::A0, Self::D(drive), Self::W(drive), Self::P(drive)]
    }

    /// Linear index in [0, 21].
    pub fn linear_index(self) -> usize {
        match self {
            Self::A0 => 0,
            Self::D(d) => 1 + d.index(),
            Self::W(d) => 8 + d.index(),
            Self::P(d) => 15 + d.index(),
        }
    }

    /// Construct from linear index [0, 21].
    pub fn from_linear_index(idx: usize) -> Option<Self> {
        if idx == 0 {
            return Some(Self::A0);
        }
        if idx >= Self::COUNT {
            return None;
        }
        let adjusted = idx - 1;
        let stage = adjusted / 7;
        let drive_idx = adjusted % 7;
        let drive = CoreDrive::from_number(drive_idx as u8 + 1)?;
        match stage {
            0 => Some(Self::D(drive)),
            1 => Some(Self::W(drive)),
            2 => Some(Self::P(drive)),
            _ => None,
        }
    }
}

impl fmt::Display for PathwayNode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::A0 => write!(f, "A0"),
            Self::D(d) => write!(f, "D{}", d.number()),
            Self::W(d) => write!(f, "W{}", d.number()),
            Self::P(d) => write!(f, "P{}", d.number()),
        }
    }
}

/// Satisfaction status for a pathway node.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PathwaySatisfaction {
    node: PathwayNode,
    score: f64,
    satisfied: bool,
}

impl PathwaySatisfaction {
    pub fn new(node: PathwayNode, score: f64, threshold: f64) -> Self {
        Self {
            node,
            score,
            satisfied: score >= threshold,
        }
    }

    pub fn node(self) -> PathwayNode {
        self.node
    }

    pub fn score(self) -> f64 {
        self.score
    }

    pub fn is_satisfied(self) -> bool {
        self.satisfied
    }
}

/// Inversion axes as defined in the CAS framework.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum InversionAxis {
    /// N: Operator inversion
    Operator,
    /// W: Domain inversion
    Domain,
    /// F: Drive inversion
    Drive,
    /// E: State inversion
    State,
    /// S: Sub-Drive inversion
    SubDrive,
    /// A: Pathway inversion
    Pathway,
    /// P: Compound inversion
    Compound,
}

impl InversionAxis {
    pub const ALL: [InversionAxis; 7] = [
        Self::Operator,
        Self::Domain,
        Self::Drive,
        Self::State,
        Self::SubDrive,
        Self::Pathway,
        Self::Compound,
    ];

    pub fn abbreviation(self) -> char {
        match self {
            Self::Operator => 'N',
            Self::Domain => 'W',
            Self::Drive => 'F',
            Self::State => 'E',
            Self::SubDrive => 'S',
            Self::Pathway => 'A',
            Self::Compound => 'P',
        }
    }

    pub fn index(self) -> usize {
        match self {
            Self::Operator => 0,
            Self::Domain => 1,
            Self::Drive => 2,
            Self::State => 3,
            Self::SubDrive => 4,
            Self::Pathway => 5,
            Self::Compound => 6,
        }
    }
}

impl fmt::Display for InversionAxis {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Operator => write!(f, "N (Operator)"),
            Self::Domain => write!(f, "W (Domain)"),
            Self::Drive => write!(f, "F (Drive)"),
            Self::State => write!(f, "E (State)"),
            Self::SubDrive => write!(f, "S (Sub-Drive)"),
            Self::Pathway => write!(f, "A (Pathway)"),
            Self::Compound => write!(f, "P (Compound)"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pathway_count() {
        assert_eq!(PathwayNode::all().len(), 22);
    }

    #[test]
    fn test_linear_index_roundtrip() {
        for node in PathwayNode::all() {
            let idx = node.linear_index();
            assert_eq!(PathwayNode::from_linear_index(idx), Some(node));
        }
        assert!(PathwayNode::from_linear_index(22).is_none());
    }

    #[test]
    fn test_prerequisite_chain() {
        for drive in CoreDrive::ALL {
            let chain = PathwayNode::chain(drive);
            assert_eq!(chain[0], PathwayNode::A0);
            assert_eq!(chain[1], PathwayNode::D(drive));
            assert_eq!(chain[2], PathwayNode::W(drive));
            assert_eq!(chain[3], PathwayNode::P(drive));

            // Check prerequisite links
            assert_eq!(chain[0].prerequisite(), None);
            assert_eq!(chain[1].prerequisite(), Some(chain[0]));
            assert_eq!(chain[2].prerequisite(), Some(chain[1]));
            assert_eq!(chain[3].prerequisite(), Some(chain[2]));
        }
    }

    #[test]
    fn test_pathway_display() {
        assert_eq!(format!("{}", PathwayNode::A0), "A0");
        assert_eq!(format!("{}", PathwayNode::D(CoreDrive::F3Vitality)), "D3");
        assert_eq!(format!("{}", PathwayNode::W(CoreDrive::F7Purpose)), "W7");
        assert_eq!(format!("{}", PathwayNode::P(CoreDrive::F1Unity)), "P1");
    }

    #[test]
    fn test_stage_progression() {
        assert_eq!(PathwayStage::Aspiration.next(), Some(PathwayStage::Drive));
        assert_eq!(PathwayStage::Drive.next(), Some(PathwayStage::Will));
        assert_eq!(PathwayStage::Will.next(), Some(PathwayStage::Proficiency));
        assert_eq!(PathwayStage::Proficiency.next(), None);

        assert_eq!(PathwayStage::Aspiration.prev(), None);
        assert_eq!(PathwayStage::Drive.prev(), Some(PathwayStage::Aspiration));
    }

    #[test]
    fn test_inversion_axes() {
        assert_eq!(InversionAxis::ALL.len(), 7);
        for (i, axis) in InversionAxis::ALL.iter().enumerate() {
            assert_eq!(axis.index(), i);
        }
    }

    #[test]
    fn test_satisfaction() {
        let sat = PathwaySatisfaction::new(PathwayNode::A0, 0.8, 0.5);
        assert!(sat.is_satisfied());
        assert_eq!(sat.score(), 0.8);

        let unsat = PathwaySatisfaction::new(PathwayNode::A0, 0.3, 0.5);
        assert!(!unsat.is_satisfied());
    }
}
