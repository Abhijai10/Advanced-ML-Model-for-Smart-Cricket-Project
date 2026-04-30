import argparse
import csv
import logging
import re
from pathlib import Path
from typing import List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_VIDEOS_DIR = PROJECT_ROOT / "data" / "raw_videos"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "data" / "annotations" / "metadata.csv"
VIDEO_EXTENSIONS = {".mov", ".mp4"}

QUALITY_PATTERN = re.compile(r"_(good|average|avg|bad)_(\d+)$", re.IGNORECASE)
IDLE_PATTERN = re.compile(r"^idle_(\d+)$", re.IGNORECASE)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def infer_quality(shot_label: str, stem: str) -> str:
    if shot_label.lower() == "idle":
        return "none"

    lower_name = stem.lower()
    if "good" in lower_name:
        return "good"
    if "average" in lower_name or "avg" in lower_name:
        return "average"
    if "bad" in lower_name:
        return "bad"
    return "unknown"


def player_from_quality_index(quality: str, clip_index: int) -> str:
    # good_01,good_02 / average_01,average_02 => playerA, and so on.
    if quality in {"good", "average"} and 1 <= clip_index <= 8:
        players = ["playerA", "playerB", "playerC", "playerD"]
        return players[(clip_index - 1) // 2]

    # bad_01 => playerA, bad_02 => playerB, bad_03 => playerC, bad_04 => playerD.
    if quality == "bad" and 1 <= clip_index <= 4:
        players = ["playerA", "playerB", "playerC", "playerD"]
        return players[clip_index - 1]

    return "unknown"


def infer_person_id(shot_label: str, stem: str) -> str:
    if shot_label.lower() == "idle":
        return "unknown"

    match = QUALITY_PATTERN.search(stem)
    if not match:
        LOGGER.warning("Unexpected filename pattern for player mapping: %s", stem)
        return "unknown"

    quality_token = match.group(1).lower()
    clip_index = int(match.group(2))
    quality = "average" if quality_token == "avg" else quality_token
    person_id = player_from_quality_index(quality, clip_index)

    if person_id == "unknown":
        LOGGER.warning("No player mapping for filename: %s", stem)
    return person_id


def collect_video_files(raw_videos_dir: Path) -> List[Path]:
    files = [
        path
        for path in raw_videos_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda p: str(p).lower())


def build_row(video_file: Path, raw_videos_dir: Path, video_index: int) -> Tuple[str, ...]:
    shot_label = video_file.parent.name
    stem = video_file.stem

    quality = infer_quality(shot_label, stem)
    if quality == "unknown":
        LOGGER.warning("Could not infer quality from filename: %s", video_file.name)

    person_id = infer_person_id(shot_label, stem)
    if shot_label.lower() == "idle" and not IDLE_PATTERN.match(stem):
        LOGGER.warning("Unexpected idle filename pattern: %s", video_file.name)

    relative_path = video_file.relative_to(raw_videos_dir).as_posix()
    use_for_v1 = "no" if shot_label.lower() == "idle" else "yes"

    return (
        f"{video_index:03d}",
        video_file.name,
        relative_path,
        shot_label,
        quality,
        person_id,
        use_for_v1,
    )


def write_metadata_csv(raw_videos_dir: Path, output_csv: Path) -> None:
    if not raw_videos_dir.exists():
        raise FileNotFoundError(f"Raw videos directory not found: {raw_videos_dir}")

    video_files = collect_video_files(raw_videos_dir)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "video_id",
        "file_name",
        "relative_path",
        "shot_label",
        "quality",
        "person_id",
        "use_for_v1",
    ]

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for index, video_file in enumerate(video_files, start=1):
            writer.writerow(build_row(video_file, raw_videos_dir, index))

    LOGGER.info("Metadata written to: %s", output_csv)
    LOGGER.info("Total videos indexed: %d", len(video_files))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate metadata.csv from cricket raw video folders."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_VIDEOS_DIR,
        help="Path to raw video dataset root (default: data/raw_videos).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV path (default: data/annotations/metadata.csv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_videos_dir = args.raw_dir.resolve()
    output_csv = args.output.resolve()
    write_metadata_csv(raw_videos_dir, output_csv)


if __name__ == "__main__":
    main()
