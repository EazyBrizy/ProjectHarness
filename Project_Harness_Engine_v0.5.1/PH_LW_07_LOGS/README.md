# PH-LW-07: фактическое evidence

`regressions-final` — все модули заново в этом задании; исторические результаты не подставлены.
Ранние core modules выполнялись во время финального редактирования только approval presentation/CSS;
все затронутые PH-LW modules запущены после этих правок. Native и installed-wheel прогоны — после freeze.
`baseline` — проверка исходных PH-LW-03/06 APIs до правок. `target-*` сохраняют первоначальные FAIL и retests.
`native-final` — первый полный run с одной тестовой гонкой; `native-retest` — 86 runtime PASS и docs PASS.
Его wrapper FAIL сохранён: doctor обнаружил устаревший manifest после добавления reports и test fix.
`runs/doctor-retest` — PASS после синхронизации manifest; NATIVE_SCOPE_VERDICT связывает эти runs.
Оба выполнялись на настоящем Windows 11 x64/NTFS/non-admin/Python 3.14, pinned Flask/Waitress и Edge/TCP.
`runs/installed-wheel-final` — независимая venv, Unicode CWD, site-packages import, launcher/doctor/health.
`browser-final` — реальные снимки финального UI, только синтетические fixtures.
Зависимости и platform общие для source runs в SOURCE_ENVIRONMENT; wheel — WHEEL_ENVIRONMENT.
Raw logs остаются в `_scratch/ph_lw_07`; опубликованные копии редактируют только приватные пути/credentials.
EVIDENCE_INDEX хранит разные raw/published hashes. Вложенные log hashes относятся к raw bytes.
FAIL/SKIP не повышаются до PASS. Automatic/Podman/egress и installer gates остаются незакрытыми.
Engine/Documentation ZIP не создавались. Финальная аттестация рабочих деревьев — `_workspace/PH_LW_07`.
