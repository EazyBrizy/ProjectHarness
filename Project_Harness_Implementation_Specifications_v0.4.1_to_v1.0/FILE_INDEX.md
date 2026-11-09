# FILE INDEX — Project Harness Implementation Specifications v0.4.1 → v1.0

**Формат статистики:** строки / слова / bytes  
**Назначение:** проверить полноту комплекта и быстро выбрать документ текущей версии.

| Файл | Версия/роль | Содержание | Статистика | SHA-256 |
|---|---|---|---:|---|
| `README.md` | Общий индекс | Baseline, порядок версий, сквозные инварианты и правила использования комплекта. | 244 / 1163 / 12819 | `5812c909ed0c…` |
| `01_Project_Harness_v0.4.1_Contract_Hardening.md` | v0.4.1 | Statuses, Brownfield approval, sensitivity taxonomy, strict PROJECT_INPUT schema и control-plane invariants. | 732 / 2969 / 31449 | `829bd2798a2c…` |
| `02_Project_Harness_v0.5.0_Implementation_Levels.md` | v0.5.0 | Implementation Levels, Stage Plans/Gates, brownfield maturity assessment и level-up. | 952 / 3668 / 42063 | `ca487d3e978a…` |
| `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` | v0.5.1 | Один local Codex CLI Executor Adapter и rootless Podman sandbox. | 819 / 2771 / 28526 | `91413b977ecf…` |
| `04_Project_Harness_v0.6.0_Git_Publication_and_Deployment.md` | v0.6.0 | Repository Adapter, exact commit, explicit push, один GitHub draft PR adapter и declared deployment route. | 887 / 2986 / 30838 | `20e8eca251b2…` |
| `05_Project_Harness_v0.6.1_Project_Skill_Lifecycle.md` | v0.6.1 | Declarative PROJECT skill CREATE/EXTEND, evaluation и activation lifecycle. | 720 / 2355 / 24310 | `49c66ad7dccd…` |
| `06_Project_Harness_v0.7.0_Parallel_Worktrees_and_Leases.md` | v0.7.0 | Два параллельных local worktree, atomic leases, conservative conflict analysis и integration batch. | 734 / 2500 / 24983 | `c6429980a728…` |
| `07_Project_Harness_v0.8.0_Remote_Control_Plane.md` | v0.8.0+ | Single-node remote multi-user control plane на SQLite WAL и local storage. | 847 / 3013 / 28712 | `3f9256b478f6…` |
| `08_Project_Harness_v1.0_Production_Stabilization.md` | v1.0 | Production scope freeze, migration chain, compatibility, qualification и release gates. | 661 / 2508 / 22353 | `27b7d42787d4…` |
| `FILE_INDEX.md` | Индекс файлов | Текущий файл; перечень и статистика комплекта. | — | см. `MANIFEST.sha256` |
| `MANIFEST.sha256` | Integrity manifest | SHA-256 всех файлов комплекта, кроме самого manifest. | — | не включает сам себя |

## Сводка

- Version-specific specifications: **8**.
- Markdown-файлы до добавления этого индекса: **9**.
- Объём README + восьми спецификаций: **6596 строк, 23933 слов, 246053 bytes**.
- Baseline sources в архив не включены; комплект содержит только новую implementation documentation.
- `MANIFEST.sha256` создаётся после этого индекса и содержит relative paths внутри корня комплекта.

## Порядок чтения

```text
README.md
→ 01 v0.4.1
→ 02 v0.5.0
→ 03 v0.5.1
→ 04 v0.6.0
→ 05 v0.6.1
→ 06 v0.7.0
→ 07 v0.8.0+
→ 08 v1.0
```

Каждый следующий документ предполагает полностью принятую предыдущую версию; реализация «через версию» не является поддерживаемым маршрутом.
