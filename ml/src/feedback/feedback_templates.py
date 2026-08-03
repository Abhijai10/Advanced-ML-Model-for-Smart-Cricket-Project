"""Editable language templates for Phase 11 feedback generation."""

from __future__ import annotations


COMPONENT_LABELS: dict[str, str] = {
    "head_stability_score": "head stability",
    "front_foot_commitment_score": "front-foot commitment",
    "lead_elbow_score": "lead elbow position",
    "knee_bend_score": "knee bend",
    "weight_transfer_score": "weight transfer",
    "follow_through_score": "follow-through",
    "rotation_score": "body rotation",
    "balance_score": "balance",
}


FEATURE_FEEDBACK: dict[str, dict[str, str]] = {
    "head_over_base_offset": {
        "issue": "Your head moved away from the stable base more than the v1 template expects.",
        "why": "A stable head helps balance, timing, and cleaner contact through the shot.",
        "tip": "Keep your head quieter and stacked over your base as the swing develops.",
    },
    "head_to_lead_knee_alignment": {
        "issue": "Your head-to-lead-knee alignment moved outside the expected range.",
        "why": "Head and front-side alignment helps keep the body organized through impact.",
        "tip": "Let your head travel with the front side instead of drifting away from the shot line.",
    },
    "upper_body_balance_offset": {
        "issue": "Your upper-body balance offset was outside the template range.",
        "why": "Upper-body balance affects control and makes the follow-through easier to stabilize.",
        "tip": "Stay tall through the torso and avoid leaning away during the swing.",
    },
    "front_foot_commitment_signal": {
        "issue": "Your front-foot commitment signal did not match the shot template.",
        "why": "Committed footwork creates a stronger base for shot execution.",
        "tip": "Move decisively into position before completing the swing.",
    },
    "lead_elbow_angle": {
        "issue": "Your lead-elbow angle moved outside the expected range.",
        "why": "Lead-elbow shape influences bat path, control, and shot direction.",
        "tip": "Maintain a stronger lead elbow through the hitting phase.",
    },
    "lead_elbow_extension_signal": {
        "issue": "Your lead-elbow extension pattern differed from the template.",
        "why": "Controlled extension helps transfer energy smoothly into the shot.",
        "tip": "Extend through the line of the ball without collapsing the lead arm early.",
    },
    "lead_knee_angle": {
        "issue": "Your lead-knee bend was outside the expected range.",
        "why": "Knee position affects base stability and weight control.",
        "tip": "Set a stable front knee and avoid over-straightening or over-collapsing it.",
    },
    "trail_knee_angle": {
        "issue": "Your trail-knee bend was outside the expected range.",
        "why": "The back leg helps load and release power through the shot.",
        "tip": "Use the back leg as a stable support while transferring into the shot.",
    },
    "weight_transfer_signal": {
        "issue": "Your weight-transfer signal did not match the expected shot pattern.",
        "why": "Good weight transfer helps turn body movement into controlled bat speed.",
        "tip": "Transfer your body weight smoothly toward the shot instead of staying stuck.",
    },
    "body_center_offset_x": {
        "issue": "Your body-center movement range was outside the template range.",
        "why": "Too much or too little center movement can affect balance and timing.",
        "tip": "Move through the shot with control, keeping your center of mass stable.",
    },
    "follow_through_height_signal": {
        "issue": "Your follow-through height differed from the expected shot pattern.",
        "why": "Follow-through height reflects how the bat and body finish after contact.",
        "tip": "Finish the shot fully while keeping the bat path controlled.",
    },
    "follow_through_extension_signal": {
        "issue": "Your follow-through extension was outside the template range.",
        "why": "A complete follow-through helps show that energy carried through the ball.",
        "tip": "Complete your follow-through instead of stopping the movement early.",
    },
    "bat_side_wrist_height_signal": {
        "issue": "Your bat-side wrist height did not match the expected finish.",
        "why": "Wrist height affects the shape and control of the shot finish.",
        "tip": "Keep the bat-side wrist moving into a controlled finish position.",
    },
    "hip_rotation_angle": {
        "issue": "Your hip-rotation range differed from the shot template.",
        "why": "Hip rotation contributes to power and body sequencing.",
        "tip": "Rotate through the hips smoothly without forcing or over-rotating.",
    },
    "hip_rotation_velocity": {
        "issue": "Your hip-rotation velocity moved outside the expected range.",
        "why": "Unstable rotation speed can disturb balance and shot timing.",
        "tip": "Use controlled hip rotation so the swing stays balanced.",
    },
    "shoulder_hip_separation": {
        "issue": "Your shoulder-hip separation differed from the expected range.",
        "why": "Separation between shoulders and hips affects rotation sequence and control.",
        "tip": "Coordinate shoulder and hip rotation instead of letting one lead too aggressively.",
    },
    "stance_width": {
        "issue": "Your stance width was outside the expected range.",
        "why": "A stable stance gives the body a reliable base for the shot.",
        "tip": "Set your stance wide enough for balance but not so wide that movement becomes restricted.",
    },
    "body_center_offset_y": {
        "issue": "Your vertical body-center offset differed from the template.",
        "why": "Vertical balance affects stability through contact and follow-through.",
        "tip": "Keep your body height controlled instead of rising or dipping abruptly.",
    },
}


GENERIC_COMPONENT_TIPS: dict[str, str] = {
    "head_stability_score": "Keep your head stable and balanced over your base.",
    "front_foot_commitment_score": "Commit your front foot earlier and build a stronger base.",
    "lead_elbow_score": "Maintain a stronger lead elbow through the shot.",
    "knee_bend_score": "Use a stable knee bend to support balance and power.",
    "weight_transfer_score": "Transfer your weight smoothly through the ball.",
    "follow_through_score": "Complete the follow-through with control.",
    "rotation_score": "Rotate the body smoothly without losing balance.",
    "balance_score": "Stay centered and balanced through the full movement.",
}


def score_band_label(score: float) -> str:
    """Return a human-readable score band."""
    if score >= 90.0:
        return "strong"
    if score >= 75.0:
        return "solid"
    if score >= 60.0:
        return "needs attention"
    return "priority issue"
