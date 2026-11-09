# Работа из чистого Git checkout на Windows

Дата: 2026-11-09. Этот маршрут предназначен для второго компьютера и проверки файлов, полученных из `main`.

## Получение и проверка

```powershell
git -c core.longpaths=true clone https://github.com/EazyBrizy/ProjectHarness.git
cd ProjectHarness
git config core.longpaths true
python -B tools/check_repository.py
```

Для уже существующего чистого checkout:

```powershell
git status --short
git pull --ff-only origin main
python -B tools/check_repository.py
```

Проверяющий script использует только standard library Python и Git. Для принятой среды движка используется Python 3.14 x64 под Windows. Проверка читает source/docs/frozen inventory, сверяет SHA-256 wheel/installer и наличие обязательного payload в Git index. Она не запускает Harness, не устанавливает зависимости и ничего не восстанавливает автоматически.

В Git должны находиться все 454 файла frozen bundle, включая 19 `.pyd` native extensions, точные wheel/installer FIX5 и опубликованные reports/evidence. Любой пропуск обязательного payload даёт FAIL. Файлы `Engine/build/` и `src/project_harness_engine.egg-info/` — 117 воспроизводимых generated entries полного acceptance manifest — отдельно обозначены как локальные.

## Разные области проверки

- `tools/check_repository.py` — принятые, versioned файлы Git checkout. Не требует `_inputs`, `_scratch`, `_tools`, `_deliverables` и `.venv`.
- `tools/check_workspace.py`, `tools/ph_lw_12_fix_integrity.py`, `tools/ph_lw_12_fix_verify.py` — исходный полный acceptance workspace. Они проверяют также generated build, оригинальные inputs, прежние archives/raw run provenance и локальную историю. В чистом clone этих данных намеренно нет; соответствующий запуск не заменяет repository check.
- Исторические acceptance manifests и отчёты не пересчитываются по урезанному Git checkout. Сохранённый GO относится к указанным в них exact bytes и ограничениям; Git file check не является новой runtime acceptance.

`_inputs`, developer runtimes, `.venv`, caches и приватные operator auth/uploads не нужно переносить в Git. Для разработки создать собственную среду и установить зависимости по сохранённым locks; команды и versions описаны в [RUNBOOK](RUNBOOK.md), раздел «Воспроизведение среды». Для запуска готового приложения доступны принятый installer и frozen bundle.

## Исправление публикации 2026-11-09

Первый commit исключал `.pyd` по общему правилу `*.py[cod]`: это оставило 19 обязательных native modules вне Git. Ещё один опубликованный `BUILD_RESULT.json` скрывался под общим `**/build/`. Добавлены узкие исключения для принятого payload и evidence. Исходники, docs, wheel, installer и package manifest FIX5 не изменялись и не пересобирались.

Automatic executor выключен. Только Windows; новые CI workflows и Engine/Documentation ZIP не создаются.
