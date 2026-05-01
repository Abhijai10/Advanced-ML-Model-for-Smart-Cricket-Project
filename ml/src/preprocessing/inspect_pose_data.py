import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class FileStats:
    file_name: str
    total_frames: int
    missing_frames: int
    low_visibility_frames: int
    missing_ratio: float
    low_visibility_ratio: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect pose JSON files for sequence length and data quality issues."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Folder containing pose JSON files.",
    )
    parser.add_argument(
        "--visibility-threshold",
        type=float,
        default=0.5,
        help="Average visibility threshold for a frame to be considered low quality.",
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=30,
        help="Flag files shorter than this frame count as too short.",
    )
    parser.add_argument(
        "--max-missing-ratio",
        type=float,
        default=0.3,
        help="Flag files when missing/empty frame ratio exceeds this value.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if args.visibility_threshold < 0.0 or args.visibility_threshold > 1.0:
        raise ValueError("--visibility-threshold must be between 0.0 and 1.0.")
    if args.min_frames < 1:
        raise ValueError("--min-frames must be >= 1.")
    if args.max_missing_ratio < 0.0 or args.max_missing_ratio > 1.0:
        raise ValueError("--max-missing-ratio must be between 0.0 and 1.0.")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def safe_load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON object must be a dictionary.")
    return data


def get_frame_landmarks(frame: Dict[str, Any]) -> List[Dict[str, Any]]:
    landmarks = frame.get("landmarks", [])
    if isinstance(landmarks, list):
        return landmarks
    return []


def average_visibility(landmarks: List[Dict[str, Any]]) -> float:
    if not landmarks:
        return 0.0
    vis_values: List[float] = []
    for landmark in landmarks:
        raw_visibility = landmark.get("visibility", 0.0)
        try:
            vis_values.append(float(raw_visibility))
        except (TypeError, ValueError):
            vis_values.append(0.0)
    return sum(vis_values) / len(vis_values)


def inspect_file(json_path: Path, visibility_threshold: float) -> FileStats:
    data = safe_load_json(json_path)
    frames = data.get("frames", [])
    if not isinstance(frames, list):
        frames = []

    total_frames = len(frames)
    missing_frames = 0
    low_visibility_frames = 0

    for frame in frames:
        if not isinstance(frame, dict):
            missing_frames += 1
            continue

        landmarks = get_frame_landmarks(frame)
        if len(landmarks) == 0:
            missing_frames += 1
            continue

        frame_avg_visibility = average_visibility(landmarks)
        if frame_avg_visibility < visibility_threshold:
            low_visibility_frames += 1

    missing_ratio = (missing_frames / total_frames) if total_frames > 0 else 0.0
    low_visibility_ratio = (
        low_visibility_frames / total_frames if total_frames > 0 else 0.0
    )

    return FileStats(
        file_name=json_path.name,
        total_frames=total_frames,
        missing_frames=missing_frames,
        low_visibility_frames=low_visibility_frames,
        missing_ratio=missing_ratio,
        low_visibility_ratio=low_visibility_ratio,
    )


def summarize(stats_list: List[FileStats]) -> Tuple[float, FileStats, FileStats]:
    avg_length = sum(item.total_frames for item in stats_list) / len(stats_list)
    shortest = min(stats_list, key=lambda x: x.total_frames)
    longest = max(stats_list, key=lambda x: x.total_frames)
    return avg_length, shortest, longest


def list_major_issues(
    stats_list: List[FileStats],
    min_frames: int,
    max_missing_ratio: float,
) -> List[str]:
    issues: List[str] = []
    for item in stats_list:
        reasons: List[str] = []
        if item.total_frames < min_frames:
            reasons.append(f"too short ({item.total_frames} < {min_frames})")
        if item.missing_ratio > max_missing_ratio:
            reasons.append(
                f"many missing frames ({item.missing_ratio:.1%} > {max_missing_ratio:.1%})"
            )
        if reasons:
            issues.append(f"- {item.file_name}: " + "; ".join(reasons))
    return issues


def print_report(
    input_dir: Path,
    visibility_threshold: float,
    min_frames: int,
    max_missing_ratio: float,
    stats_list: List[FileStats],
) -> None:
    print("=" * 72)
    print("POSE JSON INSPECTION REPORT")
    print("=" * 72)
    print(f"Input folder           : {input_dir}")
    print(f"Files analyzed         : {len(stats_list)}")
    print(f"Visibility threshold   : {visibility_threshold:.2f}")
    print(f"Too-short threshold    : < {min_frames} frames")
    print(f"Missing-frame threshold: > {max_missing_ratio:.1%}")
    print()

    avg_length, shortest, longest = summarize(stats_list)

    print("Overall sequence stats")
    print("-" * 72)
    print(f"Average sequence length: {avg_length:.2f} frames")
    print(f"Shortest sequence      : {shortest.file_name} ({shortest.total_frames} frames)")
    print(f"Longest sequence       : {longest.file_name} ({longest.total_frames} frames)")
    print()

    print("Per-file quality overview")
    print("-" * 72)
    header = (
        f"{'File':40} {'Frames':>8} {'Missing':>10} {'Low-Vis':>10} "
        f"{'Missing%':>10} {'Low-Vis%':>10}"
    )
    print(header)
    print("-" * 72)
    for item in stats_list:
        print(
            f"{item.file_name[:40]:40} "
            f"{item.total_frames:8d} "
            f"{item.missing_frames:10d} "
            f"{item.low_visibility_frames:10d} "
            f"{item.missing_ratio:10.1%} "
            f"{item.low_visibility_ratio:10.1%}"
        )
    print()

    major_issues = list_major_issues(stats_list, min_frames, max_missing_ratio)
    print("Files with major issues")
    print("-" * 72)
    if major_issues:
        for issue in major_issues:
            print(issue)
    else:
        print("None")
    print("=" * 72)


def main() -> None:
    args = parse_args()
    validate_args(args)

    json_files = list_json_files(args.input_dir)
    if not json_files:
        print(f"No JSON files found in: {args.input_dir}")
        return

    stats_list: List[FileStats] = []
    skipped_files: List[str] = []

    for json_file in json_files:
        try:
            stats_list.append(inspect_file(json_file, args.visibility_threshold))
        except Exception as exc:  # noqa: BLE001
            skipped_files.append(f"- {json_file.name}: {exc}")

    if not stats_list:
        print("No valid pose JSON files could be analyzed.")
        if skipped_files:
            print("Skipped files:")
            for line in skipped_files:
                print(line)
        return

    print_report(
        input_dir=args.input_dir,
        visibility_threshold=args.visibility_threshold,
        min_frames=args.min_frames,
        max_missing_ratio=args.max_missing_ratio,
        stats_list=stats_list,
    )

    if skipped_files:
        print("\nSkipped files (invalid format or unreadable)")
        print("-" * 72)
        for line in skipped_files:
            print(line)


if __name__ == "__main__":
    main()
