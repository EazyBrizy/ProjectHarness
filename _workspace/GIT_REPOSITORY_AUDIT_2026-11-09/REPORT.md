# Проверка и исправление переноса Project Harness через Git

Дата: 2026-11-09. Репозиторий: [EazyBrizy/ProjectHarness](https://github.com/EazyBrizy/ProjectHarness), `main`.

## Найдено

На входе локальный HEAD был `0f37227c1f7ae1866c62e217c84deb169e0558cf`, удалённый — `2a4ac52d8e1b47b9a5bbe058adb65dc3be6ae44b`. Разница — только новый `.github/README.md`. Этот commit включён fast-forward, чужие изменения сохранены.

Чистый checkout удалённого main содержал все 6154 Git blobs без потери или изменения bytes. Source — 111 файлов, standalone/embedded/frozen docs, wheel и installer совпадали с принятым FIX5. Однако первый commit не включал часть обязательного payload. Предыдущая проверка сравнила bytes уже выбранных Git blobs и не проверила полноту их набора относительно package inventory; этого было недостаточно.

| Категория | До исправления | После |
|---|---|---|
| 19 native `.pyd` в frozen bundle | Отсутствовали: глобальный `*.py[cod]` совпадает и с `.pyd` | Все включены с исходными SHA-256 |
| `PH_LW_11_LONG_PATH_LOGS/build/BUILD_RESULT.json` | Исключён правилом `**/build/` | Опубликован как прежний immutable evidence |
| 111 `Engine/build/lib` и 6 `*.egg-info` entries | Generated, намеренно вне Git | Остаются локальными; Git check их не требует |
| `_inputs`, `_scratch`, `_tools`, `_deliverables`, `.venv`, private auth/uploads | Намеренно локальные | Остаются вне Git |

Всего полный Engine acceptance manifest показывал 137 отсутствующих entries: 20 пропусков публикации и 117 generated entries. Сообщение другого компьютера «около 87 файлов» без списка путей нельзя отождествить с конкретным набором; здесь сохранён полный фактический аудит.

`tools/check_workspace.py` в чистом clone воспроизвёл FileNotFoundError для локального `_inputs/...PH_LW_05.zip`; прежний acceptance integrity helper — assertion об отсутствующем `build/lib`. Эти инструменты предназначены для полного acceptance workspace, а не для чистого Git checkout. Исходные проверки и исторические отчёты не ослаблены и не переписаны.

## Исправление

Добавлены узкие Git-исключения для принятых `.pyd` и опубликованного build evidence. Runtime binaries скопированы в Git из уже проверенного локального bundle без пересборки. Добавлен read-only `tools/check_repository.py`: Windows/Python standard library + Git, без dependencies/private inputs. Он проверяет обязательное содержимое Git index, совпадение Git blob bytes, source/docs/frozen hashes, exact package file set, wheel/installer и versioned entries acceptance manifest. Потеря нужного runtime файла остаётся FAIL.

Новый [REPOSITORY_RUNBOOK](../REPOSITORY_RUNBOOK.md) связан из AGENTS, CURRENT_TASK и RUNBOOK, чтобы Codex на втором компьютере выбирал подходящую проверку.

## Фактическая проверка

- [До исправления](BEFORE.json): FAIL, 19 missing native files и один missing evidence JSON.
- [Чистый checkout после исправления](AFTER.json): PASS; 454 frozen files, 5418 обязательных versioned entries; без `_inputs`, `_scratch`, `_tools`, `_deliverables` и `.venv` внутри clone. Interpreter запущен с `-I -S -B`, только standard library.
- [Повреждённый native payload](NEGATIVE_CORRUPTION.json): FAIL по SHA-256 и Git blob mismatch; после восстановления — PASS.
- `Harness.exe --check-package` из отдельного checkout: exit 0, без открытия UI. Documentation validator и source CLI `--version` в исходном clone также PASS.
- [Первичный аудит](FILE_AUDIT.json) фиксирует полный набор и причины пропусков. Максимальная относительная длина пути — 178; при текущей длине root все Git paths помещаются в 259 символов. Ошибок checkout не было.

Source digest остаётся `sha256:0789035971ad3488b37a3d1cc480a9c7c63effcc3c67c540630e452b77f936ae`; wheel — `22ce3cdca5fe875430d4780f163975ba896c3348fa2f30b5a88199064bec54a1`; installer — `a4c7432852aadf93fd19fa4646ef8306854369be8ff8fd941ce6d1d268cc5964`. Новая runtime acceptance не объявляется: существующий manual GO и принятые ограничения сохранены. Automatic executor выключен; полная v0.5.1 NOT RELEASED; Linux и Engine/Documentation ZIP не запускались/не создавались.

На другом Windows компьютере после сохранения своих изменений: `git pull --ff-only origin main`, затем `python -B tools/check_repository.py`.
