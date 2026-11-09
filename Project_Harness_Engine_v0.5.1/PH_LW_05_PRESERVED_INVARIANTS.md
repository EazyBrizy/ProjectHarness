# PH-LW-05 — сохранённые инварианты и ограничение scope

**v0.5.1 WIP / NOT RELEASED.**

1. Точные нормы v0.5.0/v0.5.1 и registries/schema версий предыдущего PH-LW-04 не изменялись; `PROJECT_INPUT@4`, Stage State canonical target и accepted scope/levels остаются неизменными.
2. `PROTOTYPE → ALPHA → BETA → MVP → RELEASE` только sequential formal Gate/level-up; никаких новых approval exemptions, fake PASS/evidence или изменений Brownfield/maintenance/migration/history.
3. `PROJECT_INPUT_ACCEPTED`, historical immutable Stage Reports, completed Runs и prior PH-LW checkpoints не переписываются. Import действует только на provisional intake.
4. UI/HTTP не включают `execute-current`, provider calls, host commands, automatic execution, remote binding, Git/PR/deploy. Manual handoff и explicit approvals сохраняются.
5. Каждая source revision exact-bound к source snapshot, SHA-256 и current draft fingerprint; GET/preview только read-only, при crash recovery происходит только explicit POST; не публикуется частичная source state.
6. Private quarantine и snapshots не принимают external filesystem path, ZIP `extractall`, arbitrary file writes или unsafe entry. Imported MD считается недоверенным текстом, не control instructions.
7. Установка на Windows 11/NTFS, real HTTP/Waitress/Edge и Podman/egress не проверялись и не объявляются PASS. До фактической security acceptance — **NO-GO**.
