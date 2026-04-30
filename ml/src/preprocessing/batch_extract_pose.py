import argparse
import csv
import logging
from pathlib import Path
from typing import Dict, List

from extract_pose import extract_pose_from_video, save_pose_json


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_METADATA_PATH = PROJECT_ROOT / "ml" / "data" / "annotations" / "metadata.csv"
DEFAULT_RAW_DIR = PROJECT_ROOT / "ml" / "data" / "raw_videos"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_json"
FAILURE_LOG_FILENAME = "batch_failures.csv"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch extract pose JSON files for videos marked use_for_v1=yes."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Path to metadata CSV file.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Root directory that contains raw video files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to store output pose JSON files.",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=1,
        help="Process every nth frame (default: 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be processed without running extraction.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N selected videos.",
    )
    return parser.parse_args()


def normalize_yes_no(value: str) -> str:
    return str(value).strip().lower()


def read_selected_rows(metadata_path: Path) -> List[Dict[str, str]]:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata CSV not found: {metadata_path}")

    selected: List[Dict[str, str]] = []
    with metadata_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_columns = {"video_id", "file_name", "relative_path", "use_for_v1"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "Metadata CSV is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        for row in reader:
            if normalize_yes_no(row.get("use_for_v1", "")) == "yes":
                selected.append(row)

    return selected


def build_output_json_path(output_dir: Path, video_id: str, file_name: str) -> Path:
    file_stem = Path(file_name).stem
    output_name = f"{video_id}_{file_stem}.json"
    return output_dir / output_name


def write_failure_log(output_dir: Path, failures: List[Dict[str, str]]) -> Path:
    failure_log_path = output_dir / FAILURE_LOG_FILENAME
    with failure_log_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["video_id", "file_name", "relative_path", "error"],
        )
        writer.writeheader()
        writer.writerows(failures)
    return failure_log_path


def main() -> None:
    args = parse_args()
    metadata_path = args.metadata.resolve()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    frame_skip = args.frame_skip
    dry_run = args.dry_run
    limit = args.limit

    if frame_skip < 1:
        raise ValueError("--frame-skip must be greater than or equal to 1.")
    if limit is not None and limit < 1:
        raise ValueError("--limit must be greater than or equal to 1.")

    output_dir.mkdir(parents=True, exist_ok=True)
    selected_rows = read_selected_rows(metadata_path)
    if limit is not None:
        print(f"Limit enabled: processing first {limit} selected videos")
        selected_rows = selected_rows[:limit]

    total_selected = len(selected_rows)
    processed = 0
    skipped = 0
    failed = 0
    would_process = 0
    failures: List[Dict[str, str]] = []

    for idx, row in enumerate(selected_rows, start=1):
        video_id = str(row.get("video_id", "")).strip()
        file_name = str(row.get("file_name", "")).strip()
        relative_path = str(row.get("relative_path", "")).strip()

        video_path = raw_dir / relative_path
        output_json_path = build_output_json_path(output_dir, video_id, file_name)

        if dry_run:
            print(f"[{idx}/{total_selected}] WOULD PROCESS: {file_name}")
            print(f"  input: {video_path}")
            print(f"  output: {output_json_path}")
        else:
            print(f"[{idx}/{total_selected}] Processing {file_name}")

        if output_json_path.exists():
            skipped += 1
            if dry_run:
                print("  WOULD SKIP: already processed")
            else:
                LOGGER.info("Skipped (already exists): %s", output_json_path.name)
            continue

        if not video_path.exists():
            failed += 1
            error_msg = f"missing_video_file: {video_path}"
            if dry_run:
                print("  WOULD FAIL: missing video")
            else:
                LOGGER.error(error_msg)
            failures.append(
                {
                    "video_id": video_id,
                    "file_name": file_name,
                    "relative_path": relative_path,
                    "error": error_msg,
                }
            )
            continue

        if dry_run:
            would_process += 1
            continue

        try:
            pose_data = extract_pose_from_video(
                input_video=video_path,
                frame_skip=frame_skip,
                visualize=False,
            )
            save_pose_json(pose_data, output_json_path)
            processed += 1
            LOGGER.info("Saved: %s", output_json_path.name)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            error_msg = f"pose_extraction_failed: {exc}"
            LOGGER.exception("Failed for %s", file_name)
            failures.append(
                {
                    "video_id": video_id,
                    "file_name": file_name,
                    "relative_path": relative_path,
                    "error": error_msg,
                }
            )

    if dry_run:
        print("\nDRY RUN SUMMARY")
        print(f"Total selected: {total_selected}")
        print(f"Would process: {would_process}")
        print(f"Would skip: {skipped}")
        print(f"Would fail: {failed}")
    else:
        failure_log_path = write_failure_log(output_dir, failures)
        print("\nBatch extraction summary")
        print(f"Total selected: {total_selected}")
        print(f"Processed: {processed}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Failure log: {failure_log_path}")


if __name__ == "__main__":
    main()
