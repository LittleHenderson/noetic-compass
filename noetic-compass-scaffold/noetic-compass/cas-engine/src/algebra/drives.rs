//! Drive Synthesis Algebra
//!
//! Defines the complete drive synthesis table for multiplication and division.
//! Inversion pairs resolve to F4 (Connection, the self-dual attractor).

use crate::ontology::CoreDrive;

/// Returns true if two drives form an inversion pair.
pub fn are_inversion_pair(a: CoreDrive, b: CoreDrive) -> bool {
    for &(x, y) in &CoreDrive::INVERSION_PAIRS {
        if (a == x && b == y) || (a == y && b == x) {
            return true;
        }
    }
    false
}

/// Synthesize two drives under multiplication.
///
/// Rules (from Qwen's formal verification):
/// - Same drive: result is that drive (idempotent)
/// - Inversion pair (F1↔F7, F2↔F6, F3↔F5): result is F4 (self-dual neutral)
/// - Non-paired different drives: result is the drive closer to F4 (attractor)
pub fn synthesize_drives(a: CoreDrive, b: CoreDrive) -> CoreDrive {
    if a == b {
        return a;
    }
    if are_inversion_pair(a, b) {
        return CoreDrive::F4Connection;
    }
    // Non-paired: whichever is closer to F4 (index 3 in 0-based)
    let dist_a = (a.index() as i32 - 3).unsigned_abs();
    let dist_b = (b.index() as i32 - 3).unsigned_abs();
    if dist_a <= dist_b { a } else { b }
}

/// Compute the drive ratio for division.
///
/// Rules:
/// - Same drive: identity (return that drive)
/// - Inversion pair: resolve to F1 (Unity, the base drive)
/// - Non-paired: return the drive that explains the difference
///   (the one further from F4, capturing the asymmetry)
pub fn drive_ratio(a: CoreDrive, b: CoreDrive) -> CoreDrive {
    if a == b {
        return a;
    }
    if are_inversion_pair(a, b) {
        return CoreDrive::F1Unity;
    }
    // The explanatory drive is the one further from F4
    let dist_a = (a.index() as i32 - 3).unsigned_abs();
    let dist_b = (b.index() as i32 - 3).unsigned_abs();
    if dist_a >= dist_b { a } else { b }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_same_drive_identity() {
        for drive in CoreDrive::ALL {
            assert_eq!(synthesize_drives(drive, drive), drive);
        }
    }

    #[test]
    fn test_inversion_pairs_yield_f4() {
        assert_eq!(
            synthesize_drives(CoreDrive::F1Unity, CoreDrive::F7Purpose),
            CoreDrive::F4Connection,
        );
        assert_eq!(
            synthesize_drives(CoreDrive::F2Wisdom, CoreDrive::F6Structure),
            CoreDrive::F4Connection,
        );
        assert_eq!(
            synthesize_drives(CoreDrive::F3Vitality, CoreDrive::F5Agency),
            CoreDrive::F4Connection,
        );
        // Symmetric
        assert_eq!(
            synthesize_drives(CoreDrive::F7Purpose, CoreDrive::F1Unity),
            CoreDrive::F4Connection,
        );
    }

    #[test]
    fn test_non_paired_closer_to_f4() {
        // F3 (index 2, dist 1) vs F1 (index 0, dist 3): F3 closer to F4
        assert_eq!(
            synthesize_drives(CoreDrive::F1Unity, CoreDrive::F3Vitality),
            CoreDrive::F3Vitality,
        );
    }

    #[test]
    fn test_drive_ratio_identity() {
        for drive in CoreDrive::ALL {
            assert_eq!(drive_ratio(drive, drive), drive);
        }
    }

    #[test]
    fn test_drive_ratio_inversion_yields_f1() {
        assert_eq!(
            drive_ratio(CoreDrive::F1Unity, CoreDrive::F7Purpose),
            CoreDrive::F1Unity,
        );
        assert_eq!(
            drive_ratio(CoreDrive::F2Wisdom, CoreDrive::F6Structure),
            CoreDrive::F1Unity,
        );
    }

    #[test]
    fn test_are_inversion_pair() {
        assert!(are_inversion_pair(CoreDrive::F1Unity, CoreDrive::F7Purpose));
        assert!(are_inversion_pair(CoreDrive::F7Purpose, CoreDrive::F1Unity));
        assert!(!are_inversion_pair(CoreDrive::F1Unity, CoreDrive::F2Wisdom));
        assert!(!are_inversion_pair(CoreDrive::F4Connection, CoreDrive::F4Connection));
    }
}
