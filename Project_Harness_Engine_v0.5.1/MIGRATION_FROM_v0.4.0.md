# Миграция Project Harness v0.4.0 → v0.4.1

**Документ:** Project Harness  
**Версия:** 0.4.1  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE DIRECT MIGRATION GUIDE

## 1. Область миграции

Поддерживается прямой переход Project Instance с:

```text
engine distribution: 0.4.0
canonical schema:     4
```

на:

```text
engine distribution: 0.4.1
canonical schema:     5
input contract:       PROJECT_INPUT@2
migration id:         MIG-ENGINE-0.4.0-TO-0.4.1
```

Переход не добавляет Implementation Levels, automated executor, container sandbox, Git publication, deployment или PROJECT skill authoring.

## 2. Предварительные условия

Миграция разрешена только если:

- `PROJECT_LOCK` указывает exact source version `0.4.0` и schema `4`;
- compatibility validation существующего проекта проходит;
- активный Run отсутствует;
- stored accepted input можно детерминированно преобразовать в `PROJECT_INPUT@2`;
- все material approvals остаются действительными;
- для `BROWNFIELD`/`HYBRID` отдельно подтверждён `brownfield_baseline`.

При активном Run операция завершается без изменений с required route `COMPLETE_BLOCK_OR_CANCEL_ACTIVE_RUN_BEFORE_MIGRATION`.

## 3. Миграция input contract

Преобразование v1 → v2:

- устанавливает `schema_version: 2`;
- сохраняет известные значения без семантической подмены;
- для `BROWNFIELD`/`HYBRID` добавляет непринятый шаблон `approvals.brownfield_baseline`, если поле отсутствовало;
- не удаляет неизвестные свойства: они сохраняются и перечисляются как точные validation paths;
- является идемпотентным для уже валидного v2 input.

`UNKNOWN` не преобразуется в data class. Такой input остаётся `WAITING_INPUT` до выбора одной из шести canonical sensitivity classes.

## 4. Greenfield Project Instance

```bash
python project-harness.py migrate-project --project /path/to/project
```

Операция:

1. валидирует v0.4.0 state в compatibility mode;
2. мигрирует accepted input;
3. создаёт новую current Task revision со status `DONE`, только если текущая legacy revision имеет `COMPLETED`;
4. сохраняет старую Task revision и все Run files неизменёнными;
5. копирует текущие registries и embedded runtime;
6. обновляет lock/schema/migration metadata;
7. выполняет полную v0.4.1 validation.

## 5. Brownfield и Hybrid

Сначала сформируйте `PROJECT_INPUT@2`, в котором пятое approval принято явно:

```text
approvals.brownfield_baseline.approved = true
approvals.brownfield_baseline.actor     = non-empty actor id
approvals.brownfield_baseline.approved_at = timestamp
```

Затем:

```bash
python project-harness.py migrate-project \
  --project /path/to/project \
  --input /path/to/PROJECT_INPUT_v2.yaml
```

Supplied input может отличаться от stored accepted input только формализацией `approvals.brownfield_baseline`. Иные semantic changes требуют отдельного Project Evolution route.

При успехе создаются:

- новая Brownfield Baseline revision со `status: ACCEPTED`;
- `accepted_by` со ссылкой на отдельный Decision;
- `accepted_at` из approval;
- immutable `DEC-<PROJECT>-BROWNFIELD-001@1` со status `ACCEPTED`.

Старая Brownfield Baseline revision не переписывается.

## 6. Исторические statuses

Immutable v0.4.0 records читаются так:

```text
historical Task COMPLETED → interpreted as DONE
historical Run COMPLETED  → interpreted as SUCCEEDED
```

Compatibility mapping отображается в validation report. Он не изменяет исходные bytes. Любая новая Task revision записывается с `DONE`, любой новый Run — только с canonical status из registry, включая успешный `SUCCEEDED`.

## 7. Manifest policy

Первоначальный `MANIFEST.sha256` сохраняется как baseline исходного handoff и не пересобирается поверх mutable project history. Текущее состояние проверяется командой:

```bash
python project-harness.py validate-project --project /path/to/project
```

Migration report сохраняется по пути:

```text
.harness/reports/MIG-ENGINE-0.4.0-TO-0.4.1.yaml
```

## 8. Идемпотентность

Повторный вызов возвращает `NO_ACTION` только когда:

- current lock уже указывает v0.4.1/schema 5;
- migration ID записан;
- полная v0.4.1 validation текущего проекта проходит.

Если migration marker присутствует, но state не соответствует контракту, операция завершается ошибкой, а не скрывает повреждение.

## 9. Восстановление

Миграция выполняет все semantic prechecks до записи, но не заявляет внешнюю транзакционность файловой системы. Перед миграцией следует сохранить доверенную копию Project Instance. При прерывании или validation failure восстановите её и повторите операцию после устранения причины. In-place обход failed invariant запрещён.
