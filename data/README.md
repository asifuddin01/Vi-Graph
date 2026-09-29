# Data

| Path           | Contents                                                                  |
| -------------- | ------------------------------------------------------------------------- |
| `raw/`         | Unprocessed source images                                                 |
| `synthetic/`   | Generated diagrams + ground-truth graphs (schema v2), spec §13–14         |
| `real/`        | Manually verified real-world diagrams, spec §15                           |
| `annotations/` | Ground-truth annotations, incl. inter-annotator agreement records (§15.1) |
| `splits/`      | Train/validation/test split manifests, each pinned by a hash (§16, §18.1) |

## Rules

- **Never train on the test set.** Keep one untouched benchmark set for final reporting.
- The test split must contain layouts/templates not seen in training (§16).
- Every real image records its source and license. Do not commit copyrighted images to a
  public dataset without permission (§15).
- Generated images are not committed (they are regenerable); split manifests and
  annotations are.
