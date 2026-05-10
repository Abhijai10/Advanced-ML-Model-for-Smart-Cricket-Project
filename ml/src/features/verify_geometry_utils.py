"""Phase 5.3 verification script for geometry_utils (no feature engineering here)."""

from __future__ import annotations

import math

import numpy as np

from geometry_utils import (
    calculate_angle,
    calculate_velocity_series,
    euclidean_distance,
    get_landmark,
    landmark_to_array,
    safe_max,
    safe_mean,
    safe_min,
    vector_between,
)


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tol)


def main() -> None:
    failures: list[str] = []

    def expect(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            print(f"  PASS — {name}")
        else:
            msg = f"{name}" + (f" ({detail})" if detail else "")
            print(f"  FAIL — {msg}")
            failures.append(msg)

    print("euclidean_distance (3D)")
    d1 = euclidean_distance([0.0, 0.0, 0.0], [3.0, 4.0, 0.0])
    expect("distance (0,0,0) to (3,4,0) is 5", _approx(d1, 5.0))
    d2 = euclidean_distance([1.0, 2.0, 2.0], [4.0, 6.0, 2.0])
    expect("distance (1,2,2) to (4,6,2) is 5", _approx(d2, 5.0))

    print("\nvector_between")
    v = vector_between([1.0, 0.0, 0.0], [4.0, 6.0, 0.0])
    expect(
        "vector from (1,0,0) to (4,6,0) is (3,6,0)",
        v.shape == (3,) and np.allclose(v, [3.0, 6.0, 0.0]),
        f"got {v!r}",
    )

    print("\ncalculate_angle (90°)")
    ang90 = calculate_angle([1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    expect("right angle ~90°", _approx(ang90, 90.0, tol=1e-6), f"got {ang90}")

    print("\ncalculate_angle (180°)")
    ang180 = calculate_angle([1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [-1.0, 0.0, 0.0])
    expect("straight line ~180°", _approx(ang180, 180.0, tol=1e-6), f"got {ang180}")

    print("\nsafe_mean / safe_min / safe_max (valid, None, nan)")
    messy = [10.0, 2.0, None, float("nan"), 5.0]
    expect("safe_mean skips bad values", _approx(safe_mean(messy), 17.0 / 3.0))
    expect("safe_min is 2", _approx(safe_min(messy), 2.0))
    expect("safe_max is 10", _approx(safe_max(messy), 10.0))
    expect("empty safe_mean is 0", _approx(safe_mean([]), 0.0))
    expect("empty safe_min is 0", _approx(safe_min([]), 0.0))
    expect("empty safe_max is 0", _approx(safe_max([]), 0.0))

    print("\ncalculate_velocity_series")
    vel = calculate_velocity_series([(0, 0, 0), (1, 0, 0), (3, 0, 0)])
    expect(
        "two step magnitudes [1, 2]",
        len(vel) == 2 and _approx(vel[0], 1.0) and _approx(vel[1], 2.0),
        f"got {vel}",
    )

    print("\nget_landmark (mock frame)")
    mock_frame = {
        "landmarks": [
            {"x": 0.1, "y": 0.2, "z": 0.0},
            {"x": 0.5, "y": 0.5, "z": 0.1},
            {"x": 0.9, "y": 0.1, "z": 0.0},
        ]
    }
    lm0 = get_landmark(mock_frame, 0)
    lm2 = get_landmark(mock_frame, 2)
    expect("index 0 returns dict", lm0 is not None and lm0.get("x") == 0.1)
    expect("index 2 returns dict", lm2 is not None and lm2.get("x") == 0.9)
    expect("out of range is None", get_landmark(mock_frame, 99) is None)
    expect("invalid frame is None", get_landmark({"no": "landmarks"}, 0) is None)

    print("\nlandmark_to_array (mock landmark)")
    arr = landmark_to_array({"x": 1.0, "y": 2.0, "z": 3.0})
    expect("full dict maps to xyz", np.allclose(arr, [1.0, 2.0, 3.0]), f"got {arr}")
    arr2 = landmark_to_array({"x": 0.5, "y": -0.25})
    expect(
        "missing z defaults to 0",
        np.allclose(arr2, [0.5, -0.25, 0.0]),
        f"got {arr2}",
    )

    print()
    if failures:
        print("Verification failed:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)

    print("Success: geometry_utils verification passed.")


if __name__ == "__main__":
    main()
