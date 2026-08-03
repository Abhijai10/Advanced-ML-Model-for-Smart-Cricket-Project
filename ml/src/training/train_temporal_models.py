"""Run Phase 8 temporal model training, comparison, and final evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/smart_cricket_matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/smart_cricket_cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.bilstm_classifier import BiLSTMClassifier  # noqa: E402
from models.gru_classifier import GRUClassifier  # noqa: E402
from models.model_config import TemporalClassifierConfig  # noqa: E402
from models.model_utils import count_parameters  # noqa: E402
from training.checkpointing import load_checkpoint  # noqa: E402
from training.feature_scaler import TemporalFeatureScaler  # noqa: E402
from training.metrics import compute_classification_metrics, load_class_names, save_metrics  # noqa: E402
from training.reproducibility import collect_environment, git_commit_sha, select_device, set_random_seed, write_json  # noqa: E402
from training.temporal_dataset import TemporalCricketDataset, create_dataloader  # noqa: E402
from training.trainer import TemporalTrainer  # noqa: E402
from training.training_config import DEFAULT_PHASE8_CONFIG, DEFAULT_PHASE8_PLAN, ML_ROOT, Phase8TrainingConfig  # noqa: E402


METADATA_PATH = ML_ROOT / "data" / "annotations" / "metadata.csv"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _make_model(config: Phase8TrainingConfig) -> torch.nn.Module:
    model_cfg = TemporalClassifierConfig(
        sequence_length=config.sequence_length,
        input_size=config.input_size,
        num_classes=config.num_classes,
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        dropout=config.dropout,
        gru_bidirectional=config.model_name == "bigru",
        lstm_bidirectional=True,
    )
    if config.model_name in ("bigru", "gru"):
        return GRUClassifier(model_cfg)
    if config.model_name == "bilstm":
        return BiLSTMClassifier(model_cfg)
    raise ValueError(f"Unknown model_name: {config.model_name}")


def _array_paths(dataset_dir: Path) -> dict[str, Path]:
    return {
        "X_train": dataset_dir / "X_train_sequence.npy",
        "X_val": dataset_dir / "X_val_sequence.npy",
        "X_test": dataset_dir / "X_test_sequence.npy",
        "y_train": dataset_dir / "y_train_sequence.npy",
        "y_val": dataset_dir / "y_val_sequence.npy",
        "y_test": dataset_dir / "y_test_sequence.npy",
    }


def _load_split_arrays(dataset_dir: Path) -> dict[str, np.ndarray]:
    paths = _array_paths(dataset_dir)
    arrays = {name: np.load(path) for name, path in paths.items()}
    for split in ("train", "val", "test"):
        X = arrays[f"X_{split}"]
        y = arrays[f"y_{split}"]
        if X.ndim != 3 or X.shape[1:] != (60, 32):
            raise ValueError(f"Unexpected X_{split} shape: {X.shape}")
        if y.shape != (X.shape[0],):
            raise ValueError(f"Unexpected y_{split} shape: {y.shape}")
    return arrays


def _prepare_scaled_datasets(
    config: Phase8TrainingConfig,
    run_dir: Path,
    feature_schema: dict[str, Any],
) -> tuple[dict[str, TemporalCricketDataset], TemporalFeatureScaler]:
    dataset_dir = Path(config.dataset_dir)
    arrays = _load_split_arrays(dataset_dir)
    scaler = TemporalFeatureScaler()
    X_train = scaler.fit_transform(arrays["X_train"])
    X_val = scaler.transform(arrays["X_val"])
    X_test = scaler.transform(arrays["X_test"])
    scaler.save(
        run_dir / "scaler",
        {
            "feature_schema_path": "ml/data/final_temporal/temporal_feature_schema.json",
            "dataset_version": config.dataset_version,
            "feature_columns": feature_schema.get("feature_columns", []),
        },
    )
    datasets = {
        "train": TemporalCricketDataset(dataset_dir, "train", X_override=X_train, y_override=arrays["y_train"]),
        "validation": TemporalCricketDataset(dataset_dir, "validation", X_override=X_val, y_override=arrays["y_val"]),
        "test": TemporalCricketDataset(dataset_dir, "test", X_override=X_test, y_override=arrays["y_test"]),
    }
    return datasets, scaler


def _write_history(run_dir: Path, history: list[dict[str, Any]]) -> None:
    history_dir = run_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    write_json(history_dir / "training_history.json", history)
    with (history_dir / "training_history.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)


def _plot_history(run_dir: Path, history: list[dict[str, Any]], model_name: str, run_id: str) -> None:
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    epochs = [row["epoch"] for row in history]

    def save_plot(filename: str, ylabel: str, series: list[tuple[str, list[float]]]) -> None:
        plt.figure(figsize=(7, 4))
        for label, values in series:
            plt.plot(epochs, values, marker="o", label=label)
        plt.xlabel("Epoch")
        plt.ylabel(ylabel)
        plt.title(f"{model_name} {run_id}")
        plt.legend()
        plt.tight_layout()
        plt.savefig(plots_dir / filename, dpi=150)
        plt.close()

    save_plot(
        "loss_curve.png",
        "Loss",
        [
            ("train", [row["training_loss"] for row in history]),
            ("validation", [row["validation_loss"] for row in history]),
        ],
    )
    save_plot(
        "accuracy_curve.png",
        "Accuracy",
        [
            ("train", [row["training_accuracy"] for row in history]),
            ("validation", [row["validation_accuracy"] for row in history]),
        ],
    )
    save_plot(
        "validation_f1_curve.png",
        "Validation macro F1",
        [("validation macro F1", [row["validation_macro_f1"] for row in history])],
    )


def _plot_confusion_matrix(path: Path, metrics: dict[str, Any], title: str) -> None:
    cm = np.asarray(metrics["confusion_matrix"], dtype=int)
    class_names = metrics["class_names"]
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap="Blues")
    plt.title(title)
    plt.colorbar()
    ticks = np.arange(len(class_names))
    plt.xticks(ticks, class_names, rotation=45, ha="right")
    plt.yticks(ticks, class_names)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center")
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150)
    plt.close()


def _metadata_by_file_name() -> dict[str, dict[str, Any]]:
    if not METADATA_PATH.exists():
        return {}
    df = pd.read_csv(METADATA_PATH)
    required = {"file_name", "person_id", "quality"}
    if not required.issubset(df.columns):
        return {}
    if df["file_name"].duplicated().any():
        return {}
    return {
        str(row["file_name"]): {
            "person_id": str(row["person_id"]),
            "quality": str(row["quality"]),
        }
        for _, row in df.iterrows()
    }


def _derive_quality(file_name: str) -> str:
    for quality in ("good", "average", "bad"):
        if f"_{quality}_" in file_name:
            return quality
    return "unknown"


def _prediction_rows(
    *,
    dataset_dir: Path,
    split: str,
    logits: np.ndarray,
    labels: np.ndarray,
    class_names: list[str],
    run_id: str,
    model_name: str,
    seed: int,
    epoch: int,
) -> list[dict[str, Any]]:
    index_path = dataset_dir / {
        "validation": "val_temporal_index.csv",
        "test": "test_temporal_index.csv",
    }[split]
    df = pd.read_csv(index_path)
    if len(df) != len(labels):
        raise ValueError(f"{split} index rows {len(df)} != predictions {len(labels)}")
    probs = torch.softmax(torch.as_tensor(logits), dim=1).numpy()
    preds = probs.argmax(axis=1)
    metadata_lookup = _metadata_by_file_name()
    rows: list[dict[str, Any]] = []
    for i, base in df.reset_index(drop=True).iterrows():
        pred = int(preds[i])
        true = int(labels[i])
        file_name = str(base["file_name"])
        metadata = metadata_lookup.get(file_name, {})
        row = {
            "split": split,
            "row_index": int(base["row_index"]),
            "video_id": str(base["video_id"]),
            "file_name": file_name,
            "person_id": metadata.get("person_id", "unknown"),
            "quality": metadata.get("quality", _derive_quality(file_name)),
            "true_label_index": true,
            "true_label_name": class_names[true],
            "predicted_label_index": pred,
            "predicted_label_name": class_names[pred],
            "confidence": float(probs[i, pred]),
            "correct": bool(pred == true),
            "run_id": run_id,
            "checkpoint_epoch": int(epoch),
            "model_name": model_name,
            "seed": int(seed),
        }
        for j, name in enumerate(class_names):
            row[f"probability_{name}"] = float(probs[i, j])
        rows.append(row)
    return rows


def _save_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _evaluate_model(
    *,
    model: torch.nn.Module,
    trainer: TemporalTrainer,
    loader: torch.utils.data.DataLoader,
    class_names: list[str],
    run_dir: Path,
    split: str,
    run_id: str,
    model_name: str,
    seed: int,
    epoch: int,
) -> dict[str, Any]:
    stats = trainer.evaluate_epoch(loader)
    metrics = compute_classification_metrics(stats["labels"], stats["predictions"], class_names)
    metrics["loss"] = stats["loss"]
    save_metrics(run_dir / "metrics" / f"{split}_metrics.json", metrics)
    _plot_confusion_matrix(
        run_dir / "plots" / f"{split}_confusion_matrix.png",
        metrics,
        f"{model_name} {split} confusion matrix",
    )
    rows = _prediction_rows(
        dataset_dir=Path(trainer.config.dataset_dir),
        split=split,
        logits=stats["logits"],
        labels=stats["labels"],
        class_names=class_names,
        run_id=run_id,
        model_name=model_name,
        seed=seed,
        epoch=epoch,
    )
    _save_predictions(run_dir / "predictions" / f"{split}_predictions.csv", rows)
    return metrics


def _load_label_mapping(path: Path) -> dict[str, Any]:
    mapping = _load_json(path)
    if "index_to_class" not in mapping:
        raise ValueError("label mapping missing index_to_class")
    return mapping


def run_single_experiment(
    config: Phase8TrainingConfig,
    *,
    smoke: bool = False,
) -> dict[str, Any]:
    set_random_seed(config.random_seed)
    device = select_device(config.device_preference)
    run_dir = Path(config.output_dir) / "experiments" / config.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    dataset_dir = Path(config.dataset_dir)
    manifest = _load_json(dataset_dir / "temporal_dataset_manifest.json")
    feature_schema = _load_json(dataset_dir / "temporal_feature_schema.json")
    label_mapping = _load_label_mapping(Path(config.label_mapping_path))
    class_names = load_class_names(config.label_mapping_path)

    model = _make_model(config)
    parameter_count = count_parameters(model, trainable_only=True)
    config = config.__class__(**{**config.to_dict(), "parameter_count": parameter_count})
    datasets, _scaler = _prepare_scaled_datasets(config, run_dir, feature_schema)
    loaders = {
        split: create_dataloader(
            dataset,
            batch_size=config.batch_size,
            seed=config.random_seed,
            num_workers=config.num_workers,
        )
        for split, dataset in datasets.items()
    }

    write_json(run_dir / "config.json", config.to_dict())
    write_json(
        run_dir / "environment.json",
        collect_environment(ML_ROOT.parent, device, manifest["dataset_version"]),
    )

    trainer = TemporalTrainer(
        model=model,
        model_name=config.model_name,
        config=config,
        device=device,
        class_names=class_names,
        run_dir=run_dir,
        scaler_reference=str(run_dir / "scaler"),
        label_mapping=label_mapping,
        dataset_version=str(manifest["dataset_version"]),
        git_commit_sha=git_commit_sha(ML_ROOT.parent),
    )
    history, best_payload = trainer.train(loaders["train"], loaders["validation"])
    _write_history(run_dir, history)
    _plot_history(run_dir, history, config.model_name, config.run_id)

    best_epoch = int(best_payload["epoch"])
    checkpoint = load_checkpoint(run_dir / "checkpoints" / "best.pt", map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])

    val_metrics = _evaluate_model(
        model=model,
        trainer=trainer,
        loader=loaders["validation"],
        class_names=class_names,
        run_dir=run_dir,
        split="validation",
        run_id=config.run_id,
        model_name=config.model_name,
        seed=config.random_seed,
        epoch=best_epoch,
    )

    summary = {
        "run_id": config.run_id,
        "model_name": config.model_name,
        "seed": config.random_seed,
        "smoke": smoke,
        "parameter_count": parameter_count,
        "best_epoch": best_epoch,
        "best_validation_macro_f1": float(val_metrics["macro_f1"]),
        "best_validation_accuracy": float(val_metrics["accuracy"]),
        "best_validation_loss": float(val_metrics["loss"]),
        "final_training_accuracy": float(history[-1]["training_accuracy"]),
        "train_validation_accuracy_gap": float(history[-1]["training_accuracy"] - val_metrics["accuracy"]),
        "checkpoint_path": str(run_dir / "checkpoints" / "best.pt"),
        "run_dir": str(run_dir),
    }
    write_json(run_dir / "run_summary.json", summary)
    with (run_dir / "run_summary.md").open("w", encoding="utf-8") as f:
        f.write(
            f"# Run Summary: {config.run_id}\n\n"
            f"- Model: `{config.model_name}`\n"
            f"- Seed: `{config.random_seed}`\n"
            f"- Best epoch: `{best_epoch}`\n"
            f"- Validation macro F1: `{val_metrics['macro_f1']:.4f}`\n"
            f"- Validation accuracy: `{val_metrics['accuracy']:.4f}`\n"
        )
    return summary


def _aggregate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_name in sorted({r["model_name"] for r in results}):
        group = [r for r in results if r["model_name"] == model_name]
        f1s = np.array([r["best_validation_macro_f1"] for r in group], dtype=float)
        accs = np.array([r["best_validation_accuracy"] for r in group], dtype=float)
        gaps = np.array([r["train_validation_accuracy_gap"] for r in group], dtype=float)
        losses = np.array([r["best_validation_loss"] for r in group], dtype=float)
        rows.append(
            {
                "model_name": model_name,
                "num_seeds": len(group),
                "mean_validation_macro_f1": float(f1s.mean()),
                "std_validation_macro_f1": float(f1s.std(ddof=0)),
                "mean_validation_accuracy": float(accs.mean()),
                "mean_train_validation_accuracy_gap": float(gaps.mean()),
                "mean_validation_loss": float(losses.mean()),
                "parameter_count": int(group[0]["parameter_count"]),
            }
        )
    return rows


def _select_best_model(aggregate: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        aggregate,
        key=lambda r: (
            -r["mean_validation_macro_f1"],
            r["std_validation_macro_f1"],
            abs(r["mean_train_validation_accuracy_gap"]),
            r["mean_validation_loss"],
            r["parameter_count"],
        ),
    )[0]


def _copy_best_artifacts(best_run: dict[str, Any], output_dir: Path) -> Path:
    best_dir = output_dir / "best_model"
    best_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_run["checkpoint_path"], best_dir / "checkpoint.pt")
    shutil.copytree(Path(best_run["run_dir"]) / "scaler", best_dir / "scaler", dirs_exist_ok=True)
    shutil.copy2(Path(DEFAULT_PHASE8_CONFIG.label_mapping_path), best_dir / "label_mapping.json")
    write_json(best_dir / "model_metadata.json", best_run)
    return best_dir / "checkpoint.pt"


def _final_test_evaluation(
    *,
    best_run: dict[str, Any],
    output_dir: Path,
    class_names: list[str],
) -> dict[str, Any]:
    run_dir = Path(best_run["run_dir"])
    config = Phase8TrainingConfig(**_load_json(run_dir / "config.json"))
    device = select_device(config.device_preference)
    model = _make_model(config).to(device)
    checkpoint = load_checkpoint(run_dir / "checkpoints" / "best.pt", map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])

    arrays = _load_split_arrays(Path(config.dataset_dir))
    scaler = TemporalFeatureScaler.load(run_dir / "scaler")
    X_test = scaler.transform(arrays["X_test"])
    dataset = TemporalCricketDataset(
        config.dataset_dir,
        "test",
        X_override=X_test,
        y_override=arrays["y_test"],
    )
    loader = create_dataloader(dataset, batch_size=config.batch_size, seed=config.random_seed)
    trainer = TemporalTrainer(
        model=model,
        model_name=config.model_name,
        config=config,
        device=device,
        class_names=class_names,
        run_dir=run_dir,
        scaler_reference=str(run_dir / "scaler"),
        label_mapping=_load_label_mapping(Path(config.label_mapping_path)),
        dataset_version=config.dataset_version,
        git_commit_sha=git_commit_sha(ML_ROOT.parent),
    )
    metrics = _evaluate_model(
        model=model,
        trainer=trainer,
        loader=loader,
        class_names=class_names,
        run_dir=run_dir,
        split="test",
        run_id=config.run_id,
        model_name=config.model_name,
        seed=config.random_seed,
        epoch=int(checkpoint["epoch"]),
    )
    save_metrics(output_dir / "comparisons" / "final_test_metrics.json", metrics)
    return metrics


def _write_comparison_artifacts(
    output_dir: Path,
    results: list[dict[str, Any]],
    aggregate: list[dict[str, Any]],
    selected: dict[str, Any],
    final_test_metrics: dict[str, Any] | None,
) -> None:
    comp_dir = output_dir / "comparisons"
    comp_dir.mkdir(parents=True, exist_ok=True)
    write_json(comp_dir / "per_seed_results.json", results)
    write_json(comp_dir / "model_comparison.json", aggregate)
    pd.DataFrame(aggregate).to_csv(comp_dir / "model_comparison.csv", index=False)
    with (comp_dir / "model_comparison.md").open("w", encoding="utf-8") as f:
        f.write("# Phase 8 Model Comparison\n\n")
        f.write("Selection rule: highest mean validation macro F1 across seeds, then stability and simplicity tie-breakers.\n\n")
        for row in aggregate:
            f.write(
                f"- `{row['model_name']}`: mean validation macro F1={row['mean_validation_macro_f1']:.4f}, "
                f"std={row['std_validation_macro_f1']:.4f}, mean validation accuracy={row['mean_validation_accuracy']:.4f}\n"
            )
        f.write(f"\nSelected model: `{selected['model_name']}`\n")
        if final_test_metrics:
            f.write(f"Final test macro F1: `{final_test_metrics['macro_f1']:.4f}`\n")


def _write_failure_analysis(output_dir: Path, test_metrics: dict[str, Any], best_run: dict[str, Any]) -> None:
    cm = np.asarray(test_metrics["confusion_matrix"])
    class_names = test_metrics["class_names"]
    confusions: list[tuple[int, str, str]] = []
    for i, true_name in enumerate(class_names):
        for j, pred_name in enumerate(class_names):
            if i != j and cm[i, j] > 0:
                confusions.append((int(cm[i, j]), true_name, pred_name))
    confusions.sort(reverse=True)
    report = output_dir / "phase8_failure_analysis.md"
    predictions_path = Path(best_run["run_dir"]) / "predictions" / "test_predictions.csv"
    misclassified_path = output_dir / "misclassified_samples.csv"
    misclassified = pd.DataFrame()
    if predictions_path.exists():
        predictions = pd.read_csv(predictions_path)
        misclassified = predictions[predictions["correct"] == False].copy()  # noqa: E712
        misclassified.to_csv(misclassified_path, index=False)
    with report.open("w", encoding="utf-8") as f:
        f.write("# Phase 8 Failure Analysis\n\n")
        f.write(f"Selected run: `{best_run['run_id']}`\n\n")
        f.write("## Confused Class Pairs\n\n")
        if confusions:
            for count, true_name, pred_name in confusions:
                f.write(f"- `{true_name}` predicted as `{pred_name}`: {count}\n")
        else:
            f.write("- No test-set misclassifications in the final selected checkpoint.\n")
        f.write("\n## Per-Class Notes\n\n")
        for name, vals in test_metrics["per_class"].items():
            f.write(
                f"- `{name}`: precision={vals['precision']:.4f}, "
                f"recall={vals['recall']:.4f}, f1={vals['f1']:.4f}, support={vals['support']}\n"
            )
        f.write("\n## Low-Confidence / High-Confidence Error Notes\n\n")
        if misclassified.empty:
            f.write("- No misclassified test samples were available for confidence clustering.\n")
        else:
            high_conf = misclassified.sort_values("confidence", ascending=False).head(5)
            for _, row in high_conf.iterrows():
                f.write(
                    f"- `{row['file_name']}`: true `{row['true_label_name']}`, "
                    f"predicted `{row['predicted_label_name']}`, confidence={row['confidence']:.4f}, "
                    f"person={row.get('person_id', 'unknown')}, quality={row.get('quality', 'unknown')}\n"
                )
            if "person_id" in misclassified.columns:
                f.write("\nMisclassifications by person:\n")
                for person, count in misclassified["person_id"].value_counts().items():
                    f.write(f"- `{person}`: {count}\n")
            if "quality" in misclassified.columns:
                f.write("\nMisclassifications by quality:\n")
                for quality, count in misclassified["quality"].value_counts().items():
                    f.write(f"- `{quality}`: {count}\n")
        f.write(f"\nMachine-readable misclassified samples: `{misclassified_path}`\n")
        f.write("\n## Scientific Caution\n\n")
        f.write(
            "Errors are classification observations only. They do not prove a biomechanical cause without a separate feature-level analysis.\n"
        )
        f.write(
            "The official split is sample-stratified and not person-disjoint, so these metrics represent in-distribution development performance.\n"
        )


def _write_person_heldout_status(output_dir: Path) -> None:
    payload: dict[str, Any] = {
        "status": "readiness_documented_not_run",
        "reason": (
            "The official Phase 8 model selection uses the locked 56/12/12 development split. "
            "Leave-one-player-out evaluation is scientifically useful, but with only four players it "
            "needs a separately locked validation policy before reporting numbers."
        ),
        "official_split_policy": "sample-stratified development split; not person-disjoint",
        "future_protocol_recommendation": (
            "Design a group-aware protocol with train-only scaler fitting inside every fold, "
            "a predeclared validation strategy on training players, and no fold-level test tuning."
        ),
    }
    if METADATA_PATH.exists():
        df = pd.read_csv(METADATA_PATH)
        if {"person_id", "use_for_v1"}.issubset(df.columns):
            v1 = df[df["use_for_v1"].astype(str).str.lower() == "yes"]
            payload["available_players"] = sorted(v1["person_id"].astype(str).unique().tolist())
            payload["samples_per_player"] = {
                str(k): int(v) for k, v in v1["person_id"].astype(str).value_counts().sort_index().items()
            }
    write_json(output_dir / "person_held_out_status.json", payload)


def _write_phase8_report(
    output_dir: Path,
    results: list[dict[str, Any]],
    aggregate: list[dict[str, Any]],
    selected: dict[str, Any],
    test_metrics: dict[str, Any],
) -> None:
    path = output_dir / "Phase 8 Training and Evaluation Report.md"
    with path.open("w", encoding="utf-8") as f:
        f.write("# Phase 8 Training and Evaluation Report\n\n")
        f.write("## Executive Summary\n\n")
        f.write(
            "Phase 8 trained bidirectional GRU and BiLSTM temporal shot classifiers on the official "
            "sample-stratified development split. Model selection used validation macro F1 only; the test split "
            "was evaluated after selecting the winning model.\n\n"
        )
        f.write("## Dataset Contract\n\n")
        f.write("- Input: `[B, 60, 32]`\n- Output logits: `[B, 4]`\n- Classes: cover_drive, defensive_shot, pull_shot, sweep_shot\n\n")
        f.write("## Split Protocol and Limitation\n\n")
        f.write(
            "The 56/12/12 split is deterministic and class-balanced, but not person-disjoint. "
            "The player-overlap audit found no exact sample leakage and all four players appearing across splits. "
            "Results do not prove unseen-player generalization.\n\n"
        )
        f.write("## Feature Scaling\n\n")
        f.write("Feature means and standard deviations were fitted on `X_train_sequence.npy` only, per feature over samples and timesteps.\n\n")
        f.write("## Reproducibility Controls\n\n")
        f.write(
            "Each run sets Python, NumPy, and PyTorch seeds, records environment metadata, stores the Git SHA, "
            "and uses deterministic DataLoader generators. Bitwise determinism can still vary across CPU, CUDA, and MPS backends.\n\n"
        )
        f.write("## Models and Seed Strategy\n\n")
        f.write("Models trained: `bigru`, `bilstm`. Seeds: 42, 123, 2026.\n\n")
        f.write("## Training Configuration\n\n")
        f.write(
            "Optimizer: AdamW; loss: CrossEntropyLoss; gradient clipping: enabled; scheduler: ReduceLROnPlateau; "
            "checkpoint metric: validation macro F1; test set excluded from model selection.\n\n"
        )
        f.write("## Per-Seed Validation Results\n\n")
        for row in results:
            f.write(
                f"- `{row['model_name']}` seed `{row['seed']}`: val macro F1={row['best_validation_macro_f1']:.4f}, "
                f"val accuracy={row['best_validation_accuracy']:.4f}, best epoch={row['best_epoch']}\n"
            )
        f.write("\n## Aggregate Model Comparison\n\n")
        for row in aggregate:
            f.write(
                f"- `{row['model_name']}`: mean val macro F1={row['mean_validation_macro_f1']:.4f}, "
                f"std={row['std_validation_macro_f1']:.4f}, params={row['parameter_count']}\n"
            )
        f.write(f"\n## Best Model\n\nSelected model: `{selected['model_name']}` using mean validation macro F1.\n\n")
        f.write("## Final Holdout Test Metrics\n\n")
        f.write(
            f"- Accuracy: `{test_metrics['accuracy']:.4f}`\n"
            f"- Macro precision: `{test_metrics['macro_precision']:.4f}`\n"
            f"- Macro recall: `{test_metrics['macro_recall']:.4f}`\n"
            f"- Macro F1: `{test_metrics['macro_f1']:.4f}`\n"
            f"- Weighted F1: `{test_metrics['weighted_f1']:.4f}`\n\n"
        )
        f.write("## Per-Class Metrics\n\n")
        for name, vals in test_metrics["per_class"].items():
            f.write(
                f"- `{name}`: precision={vals['precision']:.4f}, recall={vals['recall']:.4f}, "
                f"f1={vals['f1']:.4f}, support={vals['support']}\n"
            )
        f.write("\n## Confusion Matrix Interpretation\n\n")
        cm = np.asarray(test_metrics["confusion_matrix"])
        class_names = test_metrics["class_names"]
        confusions = []
        for i, true_name in enumerate(class_names):
            for j, pred_name in enumerate(class_names):
                if i != j and cm[i, j] > 0:
                    confusions.append((int(cm[i, j]), true_name, pred_name))
        if confusions:
            for count, true_name, pred_name in sorted(confusions, reverse=True):
                f.write(f"- `{true_name}` predicted as `{pred_name}`: {count}\n")
        else:
            f.write("- The selected checkpoint made no test-set misclassifications.\n")
        f.write("\n## What Phase 8 Proves / Does Not Prove\n\n")
        f.write(
            "Phase 8 proves the locked GRU/BiLSTM architectures can be trained end-to-end on the finalized temporal tensors "
            "with validation-based checkpointing and traceable evaluation artifacts. It does not prove production readiness, "
            "real-time inference behavior, or unseen-player generalization.\n"
        )
        f.write("\n## Known Limitations\n\n")
        f.write("- Small dataset: 80 total samples, 56 training samples.\n")
        f.write("- Current split is not person-disjoint.\n")
        f.write("- Velocity features are normalized displacement per standardized sequence step, not physical metres/second.\n")
        f.write("- `lead_wrist_acceleration` is an acceleration-like proxy.\n")
        f.write("- Four highly correlated feature pairs are known.\n\n")
        f.write("## Person-Held-Out Evaluation Status\n\n")
        f.write(
            "A person-held-out protocol was prepared as a documented future evaluation path, but no LOPO metric was reported "
            "because the four-player dataset requires a separately locked non-leaky validation policy.\n\n"
        )
        f.write("## Future Recommendations\n\n")
        f.write("- Plan Phase 9 shot segmentation without changing the Phase 8 checkpoint selection record.\n")
        f.write("- Add a locked group-aware unseen-player evaluation protocol before making generalization claims.\n")
        f.write("- Expand the dataset before increasing architecture complexity.\n\n")
        f.write("## Artifact Locations\n\n")
        f.write(f"- Experiments: `{output_dir / 'experiments'}`\n")
        f.write(f"- Comparison: `{output_dir / 'comparisons'}`\n")
        f.write(f"- Best model: `{output_dir / 'best_model'}`\n\n")
        f.write("## Reproduction Commands\n\n")
        f.write("```bash\nml/venv/bin/python ml/src/training/train_temporal_models.py --full\n```\n")


def run_full_phase8() -> dict[str, Any]:
    base = DEFAULT_PHASE8_CONFIG
    plan = DEFAULT_PHASE8_PLAN
    output_dir = Path(base.output_dir)
    class_names = load_class_names(base.label_mapping_path)

    smoke_config = base.__class__(**{**base.to_dict(), "max_epochs": 3, "early_stopping_patience": 2}).with_runtime(
        model_name=plan.smoke_model_name,
        random_seed=plan.smoke_seed,
        run_id=f"smoke_{plan.smoke_model_name}_{plan.smoke_seed}",
    )
    smoke_summary = run_single_experiment(smoke_config, smoke=True)
    write_json(output_dir / "experiments" / smoke_config.run_id / "SMOKE_RUN_DO_NOT_COMPARE.json", smoke_summary)

    results: list[dict[str, Any]] = []
    for model_name in plan.model_names:
        for seed in plan.seeds:
            config = base.with_runtime(
                model_name=model_name,
                random_seed=seed,
                run_id=f"{model_name}_seed{seed}",
            )
            results.append(run_single_experiment(config))

    aggregate = _aggregate_results(results)
    selected_model = _select_best_model(aggregate)
    selected_runs = [r for r in results if r["model_name"] == selected_model["model_name"]]
    selected_run = sorted(
        selected_runs,
        key=lambda r: (-r["best_validation_macro_f1"], r["best_validation_loss"]),
    )[0]
    best_checkpoint = _copy_best_artifacts(selected_run, output_dir)
    test_metrics = _final_test_evaluation(
        best_run=selected_run,
        output_dir=output_dir,
        class_names=class_names,
    )
    _write_comparison_artifacts(output_dir, results, aggregate, selected_model, test_metrics)
    _write_failure_analysis(output_dir, test_metrics, selected_run)
    _write_phase8_report(output_dir, results, aggregate, selected_model, test_metrics)
    _write_person_heldout_status(output_dir)
    return {
        "smoke": smoke_summary,
        "results": results,
        "aggregate": aggregate,
        "selected_model": selected_model,
        "selected_run": selected_run,
        "best_checkpoint": str(best_checkpoint),
        "test_metrics": test_metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run only the smoke experiment.")
    parser.add_argument("--full", action="store_true", help="Run full Phase 8 experiments.")
    args = parser.parse_args()
    if args.smoke:
        cfg = DEFAULT_PHASE8_CONFIG.__class__(**{**DEFAULT_PHASE8_CONFIG.to_dict(), "max_epochs": 3, "early_stopping_patience": 2}).with_runtime(
            model_name=DEFAULT_PHASE8_PLAN.smoke_model_name,
            random_seed=DEFAULT_PHASE8_PLAN.smoke_seed,
            run_id=f"smoke_{DEFAULT_PHASE8_PLAN.smoke_model_name}_{DEFAULT_PHASE8_PLAN.smoke_seed}",
        )
        summary = run_single_experiment(cfg, smoke=True)
        print(json.dumps(summary, indent=2))
        return 0
    if args.full:
        result = run_full_phase8()
        print(json.dumps({
            "selected_model": result["selected_model"],
            "selected_run": result["selected_run"],
            "test_metrics": result["test_metrics"],
        }, indent=2))
        return 0
    parser.error("Use --smoke or --full")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
