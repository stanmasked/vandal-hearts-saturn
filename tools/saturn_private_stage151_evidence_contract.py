"""Stage151: validate exact private pair and four-control evidence schemas.

Verifies internal evidence contracts only. It does NOT authenticate the source
process, original disc provenance, runner binary, or owner-only Drive readback.
Those independent duties stay with Stage149/Stage150's private runner gates.
"""
from __future__ import annotations

from tools.saturn_private_stage147_replay_matrix import LABELS, PAIR_INDEXES

PAIR_EXPECTED = {
    144: {"kind": "STAGE144_PRIVATE_PROLOGUE_CONTINUE_ELEVENTH_C_INTEGRITY_ONLY",
          "frames": 132000, "pngs": 1100, "pre": 999, "press": 120000,
          "release": 120006, "early_end": 121200},
    145: {"kind": "STAGE145_PRIVATE_PROLOGUE_CONTINUE_TWELFTH_C_INTEGRITY_ONLY",
          "frames": 144000, "pngs": 1200, "pre": 1099, "press": 132000,
          "release": 132006, "early_end": 133200},
}
COMPARISON_KEYS = tuple(f"{LABELS[a]}__{LABELS[b]}" for a, b in PAIR_INDEXES)
CROSS_KEYS = ("stage144_a__stage145_a", "stage144_a__stage145_b",
              "stage144_b__stage145_a", "stage144_b__stage145_b")
CLASSIFICATIONS = frozenset({
    "within_build_replay_consistency_not_established",
    "decoded_prefix_and_within_build_diagnostics_aligned",
    "repeatable_cross_build_pixel_difference_candidate",
    "cross_build_pixel_difference_not_reproducible",
})


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _expect(data: dict, key: str, value) -> None:
    if data.get(key) != value or type(data.get(key)) is not type(value):
        raise ValueError("Stage151 evidence contract field invalid: " + key)


def validate_private_pair_report(report: dict, stage: int) -> None:
    if type(stage) is not int or stage not in PAIR_EXPECTED or not isinstance(report, dict):
        raise ValueError("Stage151 pair stage/report invalid")
    c = PAIR_EXPECTED[stage]
    _expect(report, "schema", f"vh-saturn-stage{stage}-private-pair-run-1")
    _expect(report, "stage", stage)
    _expect(report, "run_exit_status", 0)
    for key in ("both_private_processes_returned_zero_status",
                "runner_sha256_matches_pinned_release",
                "original_media_unchanged_before_after", "runner_unchanged_before_after"):
        _expect(report, key, True)
    for key in ("original_media_or_frame_hashes_exported",
                "full_playable_battle_or_unit_control_verified"):
        _expect(report, key, False)
    if stage == 144:
        for key in ("stage124_drive_readback_receipt_verified",
                    "stage143_drive_readback_receipt_verified"):
            _expect(report, key, True)
        gate = report.get("stage143_owner_only_drive_readback_gate")
        if not isinstance(report.get("stage124_archive_integrity_gate"), dict):
            raise ValueError("Stage151 Stage124 archive integrity gate absent")
        required_gate = "stage143_owner_only_drive_readback_verified"
    else:
        _expect(report, "stage144_drive_readback_receipt_verified", True)
        gate = report.get("stage144_owner_only_drive_readback_gate")
        required_gate = "stage144_owner_only_drive_readback_verified"
    if not isinstance(gate, dict) or gate.get(required_gate) is not True:
        raise ValueError("Stage151 owner-only predecessor readback gate unverified")

    audit = report.get("paired_capture_audit")
    if not isinstance(audit, dict):
        raise ValueError("Stage151 paired capture audit missing")
    exact = {
        "schema_version": 1, "kind": c["kind"],
        "frames_per_process": c["frames"],
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": c["pngs"],
        "same_dimensions_across_runs": True,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "shared_tenth_C_press_frame": 108000,
        "shared_tenth_C_release_frame": 108006,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
        "cd_logs_differ": False,
    }
    if stage == 144:
        exact.update({
            "eleventh_C_press_frame": c["press"],
            "eleventh_C_release_frame": c["release"],
            "pre_eleventh_checkpoint_equal_count": c["pre"],
            "pre_eleventh_checkpoint_total": c["pre"],
        })
        early = "first_post_eleventh_framebuffer_divergence_by_121200"
        final = "first_post_eleventh_framebuffer_divergence_through_132000"
    else:
        exact.update({
            "shared_eleventh_C_press_frame": 120000,
            "shared_eleventh_C_release_frame": 120006,
            "twelfth_C_press_frame": c["press"],
            "twelfth_C_release_frame": c["release"],
            "twelfth_press_checkpoint_equal": True,
            "pre_twelfth_checkpoint_equal_count": c["pre"],
            "pre_twelfth_checkpoint_total": c["pre"],
        })
        early = "first_post_twelfth_framebuffer_divergence_by_133200"
        final = "first_post_twelfth_framebuffer_divergence_through_144000"
    for key, value in exact.items():
        _expect(audit, key, value)
    for key in ("control_cd_event_count", "intervention_cd_event_count"):
        if not _integer(audit.get(key), 1, 2_000_000):
            raise ValueError("Stage151 CD event count invalid")
    if audit["control_cd_event_count"] != audit["intervention_cd_event_count"]:
        raise ValueError("Stage151 control/intervention CD events disagree")
    early_value = audit.get(early)
    final_value = audit.get(final)
    if (not _integer(early_value, c["press"] + 120, c["early_end"])
            or not _integer(final_value, c["press"] + 120, c["frames"])
            or early_value % 120 or final_value % 120
            or final_value != early_value):
        raise ValueError("Stage151 post-confirm framebuffer divergence inconsistent")
    end_key = "frame_132000_differs" if stage == 144 else "frame_144000_differs"
    if type(audit.get(end_key)) is not bool:
        raise ValueError("Stage151 terminal framebuffer witness malformed")


def _decode_ranges(entry: dict) -> tuple[int, ...]:
    count = entry.get("pixel_mismatch_count")
    ranges = entry.get("pixel_mismatch_ranges")
    first = entry.get("first_pixel_mismatch_frame")
    if not _integer(count, 0, 800) or not isinstance(ranges, list):
        raise ValueError("Stage151 pixel mismatch metadata malformed")
    decoded = []
    for r in ranges:
        if not isinstance(r, dict):
            raise ValueError("Stage151 pixel mismatch range is not an object")
        a, b, n = r.get("start_frame"), r.get("end_frame"), r.get("checkpoint_count")
        if (not _integer(a, 120, 96000) or not _integer(b, a, 96000) or
                (a % 120 != 0) or (b % 120 != 0) or
                not _integer(n, 1, 800) or n != (b - a) // 120 + 1):
            raise ValueError("Stage151 pixel mismatch range malformed")
        if decoded and a <= decoded[-1]:
            raise ValueError("Stage151 pixel mismatch ranges overlap")
        decoded.extend(range(a, b + 1, 120))
    if len(decoded) != count or (decoded[0] if decoded else None) != first:
        raise ValueError("Stage151 pixel mismatch ranges do not reproduce totals")
    return tuple(decoded)


def validate_private_replay_matrix(matrix: dict) -> None:
    if not isinstance(matrix, dict):
        raise ValueError("Stage151 replay matrix missing")
    for key, value in {
        "schema": "vh-saturn-stage147-four-control-replay-matrix-1",
        "kind": "STAGE147_PRIVATE_CONTROL_REPLAY_MATRIX",
        "labels": list(LABELS),
        "checkpoint_count": 800, "frame_start": 120,
        "frame_end": 96000, "frame_step": 120,
        "runner_sha256_independently_verified_by_this_tool": False,
        "same_host_and_disc_provenance_independently_verified": False,
        "caller_must_verify_full_paired_capture_audits_and_same_host_media": True,
        "source_level_causality_established": False,
        "original_media_or_frame_hashes_exported": False,
        "private_pixel_hashes_exported": False,
        "battle_or_tactical_player_control_verified": False,
    }.items():
        _expect(matrix, key, value)
    cmp = matrix.get("comparisons")
    if not isinstance(cmp, dict) or set(cmp) != set(COMPARISON_KEYS):
        raise ValueError("Stage151 replay matrix must have exactly six comparisons")
    decoded = {}
    for name in COMPARISON_KEYS:
        entry = cmp[name]
        if not isinstance(entry, dict):
            raise ValueError("Stage151 comparison missing")
        decoded[name] = _decode_ranges(entry)
        for key in ("sh2_record_mismatch_count", "video_record_mismatch_count"):
            if not _integer(entry.get(key), 0, 801):
                raise ValueError("Stage151 diagnostic count malformed")
        if not _integer(entry.get("fad_common_prefix_record_count"), 0, 5_000_000):
            raise ValueError("Stage151 FAD comparison count malformed")
        if type(entry.get("fad_equal")) is not bool:
            raise ValueError("Stage151 FAD equality flag malformed")
    inner = (cmp["stage144_a__stage144_b"], cmp["stage145_a__stage145_b"])
    pixels_equal = all(e["pixel_mismatch_count"] == 0 for e in inner)
    diag_equal = all(e["sh2_record_mismatch_count"] == 0 and
                     e["video_record_mismatch_count"] == 0 and e["fad_equal"]
                     for e in inner)
    uniform = all(decoded[k] == decoded[CROSS_KEYS[0]] for k in CROSS_KEYS[1:])
    _expect(matrix, "within_build_pixels_equal", pixels_equal)
    _expect(matrix, "within_build_diagnostics_and_fad_equal", diag_equal)
    _expect(matrix, "cross_build_mismatch_patterns_equal", uniform)
    if not (pixels_equal and diag_equal):
        classification = "within_build_replay_consistency_not_established"
    elif uniform and not decoded[CROSS_KEYS[0]]:
        classification = "decoded_prefix_and_within_build_diagnostics_aligned"
    elif uniform:
        classification = "repeatable_cross_build_pixel_difference_candidate"
    else:
        classification = "cross_build_pixel_difference_not_reproducible"
    _expect(matrix, "classification", classification)
