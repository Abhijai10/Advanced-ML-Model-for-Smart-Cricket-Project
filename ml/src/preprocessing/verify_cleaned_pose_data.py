import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_cleaned"


@dataclass
class VerificationResult:
    file_name: str
    passed: bool
    frame_count: int
    issues: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify integrity of cleaned pose JSON files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing cleaned pose JSON files.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def verify_one_file(json_path: Path) -> VerificationResult:
    issues: List[str] = []
    frame_count = 0

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        return VerificationResult(
            file_name=json_path.name,
            passed=False,
            frame_count=0,
            issues=[f"Invalid JSON or unreadable file: {exc}"],
        )

    if not isinstance(data, dict):
        return VerificationResult(
            file_name=json_path.name,
            passed=False,
            frame_count=0,
            issues=["Top-level JSON must be an object."],
        )

    frames = data.get("frames")
    if not isinstance(frames, list):
        return VerificationResult(
            file_name=json_path.name,
            passed=False,
            frame_count=0,
            issues=["Missing or invalid 'frames' list."],
        )

    frame_count = len(frames)
    if frame_count == 0:
        issues.append("File has zero frames after cleaning.")

    for frame_index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            issues.append(f"Frame {frame_index}: frame must be an object.")
            continue

        landmarks = frame.get("landmarks")
        if not isinstance(landmarks, list):
            issues.append(f"Frame {frame_index}: missing or invalid landmarks list.")
            continue

        if len(landmarks) == 0:
            issues.append(f"Frame {frame_index}: landmarks list is empty.")
            continue

        for landmark_index, landmark in enumerate(landmarks):
            if not isinstance(landmark, dict):
                issues.append(
                    f"Frame {frame_index}, landmark {landmark_index}: "
                    "landmark must be an object."
                )
                continue

            for key in ("x", "y", "z"):
                if key not in landmark:
                    issues.append(
                        f"Frame {frame_index}, landmark {landmark_index}: missing '{key}'."
                    )
                elif not is_numeric(landmark.get(key)):
                    issues.append(
                        f"Frame {frame_index}, landmark {landmark_index}: "
                        f"'{key}' is not numeric."
                    )

            # Visibility is optional in verification: safe if missing.
            if "visibility" in landmark and not is_numeric(landmark.get("visibility")):
                issues.append(
                    f"Frame {frame_index}, landmark {landmark_index}: "
                    "'visibility' exists but is not numeric."
                )

    return VerificationResult(
        file_name=json_path.name,
        passed=len(issues) == 0,
        frame_count=frame_count,
        issues=issues,
    )


def print_report(results: List[VerificationResult]) -> None:
    total_files = len(results)
    passed_files = sum(1 for result in results if result.passed)
    failed_files = total_files - passed_files

    non_zero_frame_results = [result for result in results if result.frame_count > 0]
    shortest = min(non_zero_frame_results, key=lambda x: x.frame_count, default=None)
    longest = max(non_zero_frame_results, key=lambda x: x.frame_count, default=None)

    print("=" * 72)
    print("CLEANED POSE DATA VERIFICATION REPORT")
    print("=" * 72)
    print(f"Total files checked : {total_files}")
    print(f"Files passed        : {passed_files}")
    print(f"Files failed        : {failed_files}")
    if shortest is not None:
        print(
            f"Shortest sequence   : {shortest.file_name} "
            f"({shortest.frame_count} frames)"
        )
    else:
        print("Shortest sequence   : N/A")
    if longest is not None:
        print(
            f"Longest sequence    : {longest.file_name} "
            f"({longest.frame_count} frames)"
        )
    else:
        print("Longest sequence    : N/A")
    print("-" * 72)

    failed_results = [result for result in results if not result.passed]
    if not failed_results:
        print("No issues found. All cleaned files passed integrity checks.")
    else:
        print("Issues found:")
        for result in failed_results:
            print(f"\n- {result.file_name}")
            for issue in result.issues:
                print(f"  * {issue}")

    print("=" * 72)


def main() -> None:
    args = parse_args()
    validate_args(args)

    input_dir = args.input_dir.resolve()
    json_files = list_json_files(input_dir)
    if not json_files:
        print(f"No JSON files found in: {input_dir}")
        return

    results = [verify_one_file(path) for path in json_files]
    print_report(results)


if __name__ == "__main__":
    main()
