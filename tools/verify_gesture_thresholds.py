#!/usr/bin/env python3
"""
verify_gesture_thresholds.py — Numeric verification for gesture threshold constants
iOS 27.2 build 24B119 — Gesture Recognizer Arbitration Engine RE
"""
import json, struct, math, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def verify_range(name: str, value: float, min_val: float, max_val: float) -> bool:
    ok = min_val <= value <= max_val
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}: {value} (expected {min_val}–{max_val})")
    return ok

def run_all_verifications():
    threshold_file = ROOT / "artifacts/gesture/per_gesture_threshold_table.json"
    edge_file = ROOT / "artifacts/gesture/edge_gesture_config.json"
    
    if not threshold_file.exists():
        print(f"ERROR: Missing threshold table: {threshold_file}")
        return False
    if not edge_file.exists():
        print(f"ERROR: Missing edge config: {edge_file}")
        return False

    data = json.loads(threshold_file.read_text())
    edge_data = json.loads(edge_file.read_text())
    
    thresholds = data["thresholds"]
    edge_gestures = edge_data["edge_gestures"]
    
    all_pass = True
    print("=== Gesture Threshold & Kinetic Verification ===")
    
    # 1. Pan slop tiers (pre-confirmed from scrolling RE)
    pan_slop = thresholds.get("Pan", {}).get("slop_tiers_pt", [])
    if pan_slop == [10, 4, 2, 0]:
        print("  [PASS] Pan slop tiers: [10, 4, 2, 0] pt — matches scrolling RE")
    else:
        print(f"  [FAIL] Pan slop tiers: {pan_slop} — expected [10, 4, 2, 0]")
        all_pass = False

    # Pan lock break & velocity decay
    lock_break = thresholds.get("Pan", {}).get("lock_break_slop_pt", {}).get("value", 0)
    all_pass &= verify_range("Pan lock_break_slop_pt", lock_break, 20.0, 100.0)
    
    vel_decay = thresholds.get("Pan", {}).get("velocity_decay_tau_ms", {}).get("value", 0)
    all_pass &= verify_range("Pan velocity_decay_tau_ms", vel_decay, 10.0, 100.0)

    # 2. Tap & DoubleTap
    tap_slop = thresholds.get("Tap", {}).get("move_slop_pt", {}).get("value", 0)
    all_pass &= verify_range("Tap move_slop_pt", tap_slop, 1.0, 50.0)

    tap_dur = thresholds.get("Tap", {}).get("max_duration_ms", {}).get("value", 0)
    all_pass &= verify_range("Tap max_duration_ms", tap_dur, 100.0, 1000.0)

    double_tap_int = thresholds.get("DoubleTap", {}).get("max_inter_tap_ms", {}).get("value", 0)
    all_pass &= verify_range("DoubleTap max_inter_tap_ms", double_tap_int, 100.0, 1000.0)

    double_tap_sep = thresholds.get("DoubleTap", {}).get("inter_tap_separation_tolerance_pt", {}).get("value", 0)
    all_pass &= verify_range("DoubleTap inter_tap_separation_tolerance_pt", double_tap_sep, 20.0, 100.0)

    # 3. Long Press
    lp = thresholds.get("LongPress", {}).get("min_duration_ms", {}).get("value", 0)
    all_pass &= verify_range("LongPress min_duration_ms", lp, 100.0, 2000.0)

    lp_slop = thresholds.get("LongPress", {}).get("move_slop_pt", {}).get("value", 0)
    all_pass &= verify_range("LongPress move_slop_pt", lp_slop, 1.0, 50.0)

    # 4. Swipe
    sw_vel = thresholds.get("Swipe", {}).get("min_velocity_ptps", {}).get("value", 0)
    all_pass &= verify_range("Swipe min_velocity_ptps", sw_vel, 20.0, 3000.0)

    sw_slop = thresholds.get("Swipe", {}).get("move_slop_pt", {}).get("value", 0)
    all_pass &= verify_range("Swipe move_slop_pt", sw_slop, 5.0, 50.0)

    sw_perp = thresholds.get("Swipe", {}).get("max_perpendicular_pt", {}).get("value", 0)
    all_pass &= verify_range("Swipe max_perpendicular_pt", sw_perp, 5.0, 40.0)

    # 5. Pinch & Rotation
    pinch_scale = thresholds.get("Pinch", {}).get("min_scale_delta", {}).get("value", 0)
    all_pass &= verify_range("Pinch min_scale_delta", pinch_scale, 0.005, 0.10)

    rot_rad = thresholds.get("Rotation", {}).get("min_rotation_radians", {}).get("value", 0)
    all_pass &= verify_range("Rotation min_rotation_radians", rot_rad, 0.01, 0.50)

    # 6. Edge Gestures
    print("\n=== Edge Gesture Subsystem Verification ===")
    back_inset = edge_gestures.get("Back", {}).get("edge_inset_pt", {}).get("value", 0)
    all_pass &= verify_range("Back edge_inset_pt", back_inset, 5.0, 30.0)

    back_vel = edge_gestures.get("Back", {}).get("min_velocity_ptps", {}).get("value", 0)
    all_pass &= verify_range("Back min_velocity_ptps", back_vel, 20.0, 200.0)

    nc_inset = edge_gestures.get("NotificationCentre", {}).get("top_inset_height_pt", {}).get("value", 0)
    all_pass &= verify_range("NotificationCentre top_inset_height_pt", nc_inset, 10.0, 50.0)

    nc_vel = edge_gestures.get("NotificationCentre", {}).get("min_velocity_ptps", {}).get("value", 0)
    all_pass &= verify_range("NotificationCentre min_velocity_ptps", nc_vel, 100.0, 500.0)

    cc_inset = edge_gestures.get("ControlCentre", {}).get("top_inset_height_pt", {}).get("value", 0)
    all_pass &= verify_range("ControlCentre top_inset_height_pt", cc_inset, 10.0, 50.0)

    cc_fraction = edge_gestures.get("ControlCentre", {}).get("right_fraction", {}).get("value", 0)
    all_pass &= verify_range("ControlCentre right_fraction", cc_fraction, 0.15, 0.50)

    reach_bar = edge_gestures.get("Reachability", {}).get("home_bar_region_height_pt", {}).get("value", 0)
    all_pass &= verify_range("Reachability home_bar_region_height_pt", reach_bar, 20.0, 50.0)

    reach_vel = edge_gestures.get("Reachability", {}).get("min_velocity_ptps", {}).get("value", 0)
    all_pass &= verify_range("Reachability min_velocity_ptps", reach_vel, 50.0, 300.0)

    reach_disp = edge_gestures.get("Reachability", {}).get("min_downward_displacement_pt", {}).get("value", 0)
    all_pass &= verify_range("Reachability min_downward_displacement_pt", reach_disp, 5.0, 30.0)

    return all_pass

if __name__ == "__main__":
    ok = run_all_verifications()
    print(f"\n{'✅ ALL PASSED' if ok else '❌ SOME FAILURES'}")
    sys.exit(0 if ok else 1)
