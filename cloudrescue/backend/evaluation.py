import json
from statistics import mean

from backend.config import SERVICES
from backend.replay import SCENARIOS, scenario_result


def evaluate() -> dict:
    results = {name: scenario_result(name) for name in SCENARIOS}
    tp = fp = fn = tn = exact = 0
    detection: list[float] = []
    diagnosis: list[float] = []
    rows = []
    for name, result in results.items():
        truth = set(result["ground_truth"])
        predicted = set(result["predictions"])
        tp += len(truth & predicted)
        fp += len(predicted - truth)
        fn += len(truth - predicted)
        tn += len(set(SERVICES) - truth - predicted)
        exact += int(truth == predicted)
        start = result["fault_started"]
        detection.extend(at - start for at in result["first_detection"].values())
        diagnosis.extend(
            result["first_diagnosis"][service] - start for service in truth & predicted
        )
        rows.append(
            {
                "id": name,
                **{
                    key: result[key]
                    for key in (
                        "title",
                        "ground_truth",
                        "predictions",
                        "first_detection",
                        "first_diagnosis",
                    )
                },
            }
        )
    return {
        "synthetic": True,
        "scenarios": rows,
        "exact_matches": exact,
        "accuracy": exact / len(results),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "mean_detection_seconds": mean(detection) if detection else None,
        "mean_diagnosis_seconds": mean(diagnosis) if diagnosis else None,
        "detection_samples": len(detection),
        "diagnosis_samples": len(diagnosis),
        "calibration": None,
        "calibration_reason": "Five scripted scenarios are insufficient for confidence calibration.",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
