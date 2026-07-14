# Phase 8 Model Comparison

Selection rule: highest mean validation macro F1 across seeds, then stability and simplicity tie-breakers.

- `bigru`: mean validation macro F1=0.8353, std=0.0031, mean validation accuracy=0.8333
- `bilstm`: mean validation macro F1=0.7236, std=0.0471, mean validation accuracy=0.7222

Selected model: `bigru`
Final test macro F1: `0.6762`
