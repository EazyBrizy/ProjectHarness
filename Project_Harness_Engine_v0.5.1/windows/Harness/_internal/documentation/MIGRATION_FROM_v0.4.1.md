# Миграция Project Harness v0.4.1 → v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE MIGRATION GUIDE

## 1. Boundary

```text
source engine:       0.4.1
source schema:       5
source input:        PROJECT_INPUT@2
target engine:       0.5.0
target schema:       6
target input:        PROJECT_INPUT@3
migration id:        MIG-ENGINE-0.4.1-TO-0.5.0
```

Поддерживается только прямой переход с валидного v0.4.1 Project Instance. Более ранние версии сначала мигрируют последовательно до v0.4.1.

## 2. Неизменяемые гарантии

Migration:

- не переписывает completed Task/Run/Evidence/Decision files;
- не выводит accepted level из старого `COMPLETED`;
- не присваивает `RELEASE` по имени версии или документации;
- не изменяет source directory до полной проверки target copy;
- не пропускает Stage;
- не создаёт executable future-stage prompts;
- записывает migration report и lock metadata;
- повторно возвращает `NO_ACTION` только после full current-state validation.

## 3. Required target decision

v0.5.0 требует `implementation.target_level`. Автоматический guess запрещён. Для Greenfield `claimed_current_level` равен `NONE`; для Brownfield/Hybrid при отсутствии доказанного заявления используется `UNKNOWN`.

Если migrated input не содержит target, readiness остаётся `WAITING_INPUT`. Если пользователь выбрал `UNSURE`, требуется recommendation/decision flow и `WAITING_DECISION`.

## 4. Command

**Оператор v0.5.0:** этот документ остаётся migration contract, а не прежним фактом о v0.4.1. Для фактических команд source/wheel, `validate-project`, сохранения immutable history и последующего отдельного Brownfield assessment см. операторский runbook PH-F07 (в архиве Documentation: `08_Distribution/04_Operator_Runbook_v0.5.0.md`). Поддерживается только direct v0.4.1/schema 5 → v0.5.0/schema 6; актуальный input — строго approved `PROJECT_INPUT@3`.

```bash
python project-harness.py migrate-project   --project /path/to/extracted-v0.4.1-project   --input /path/to/PROJECT_INPUT_v3.yaml
```

`--input` должен быть strict approved `PROJECT_INPUT@3`, совместимый с принятой v0.4.1 semantic baseline и содержащий target implementation level.

## 5. Transaction model

1. Проверить source lock, schema, registries и отсутствие unsafe active transition.
2. Создать isolated migration copy рядом с source project.
3. Сохранить immutable historical files byte-for-byte.
4. Установить engine 0.5.0, schema 6 и registry locks.
5. Создать Stage State, Stage Plans и Stage Gates.
6. Нормализовать current route в зависимости от history.
7. Пересобрать generated views и embedded runtime.
8. Выполнить full mutable-project validation копии.
9. Только после PASS атомарно заменить target directory.
10. При любой ошибке удалить/изолировать copy и оставить source project неизменным.

## 6. Проект без выполненных задач

Для подготовленного handoff, где product Tasks не выполнялись:

- target обязателен;
- создаётся последовательный Stage path;
- только `PROTOTYPE` становится active;
- planning старого all-scope route supersede’ится;
- создаётся новый active-stage detailed DAG;
- future stages получают outlines без executable bundles;
- current JIT bundle компилируется для первой READY Task active stage.

## 7. Проект с completed history

Completed history сохраняется, но не является Stage acceptance evidence сама по себе. Migration создаёт conservative read-only maturity assessment/review route:

- claimed, observed и accepted values разделены;
- previous accepted level остаётся `NONE`, пока нет formal baseline approval;
- existing product state анализируется как Brownfield baseline;
- missing execution evidence получает `UNKNOWN`;
- после approval предыдущие satisfied stages принимаются последовательно с отдельными reports;
- active stage выбирается только после commit acceptance transaction.

## 8. Canonical paths

```text
.harness/stages/STAGE_STATE.yaml
.harness/stages/PLANS/
.harness/stages/GATES/
.harness/stages/ACCEPTANCE/
.harness/stages/ASSESSMENTS/
.harness/stages/STATE_HISTORY/
.harness/stages/TRANSACTIONS/
```

Имена каталогов uppercase являются normative contract paths.

## 9. Project Lock changes

Lock обновляет:

- `harness_distribution: 0.5.0`;
- `schema_version: 6`;
- exact versions/digests seven registries;
- `migrated_from: 0.4.1`;
- `migrated_from_schema_version: 5`;
- applied `MIG-ENGINE-0.4.1-TO-0.5.0`;
- migration timestamp/report reference.

Historical records продолжают ссылаться на собственные historical assumptions и target. Validator не переоценивает старый prompt bundle относительно нового target.

## 10. Failure and recovery

| Failure | Required behavior |
|---|---|
| Source version/schema не 0.4.1/5 | отказ без изменений |
| Target отсутствует | `WAITING_INPUT` |
| Input нарушает strict schema | exact validation errors |
| Active/unsafe Run | migration blocked |
| Copy validation fails | rollback; source unchanged |
| Partial filesystem commit | restore previous directory/transaction state |
| Repeated successful migration | full validation, затем `NO_ACTION` |

## 11. Verification checklist

- source tree digest unchanged on failed migration;
- immutable history digests identical before/after;
- Stage path sequential to target;
- exactly one active stage;
- no Task/Prompt Bundle from future stage runnable;
- legacy completed history not mapped to accepted level automatically;
- migration report present;
- lock versions/digests exact;
- `validate-project` PASS;
- rerun is idempotent.

## 12. Scope

Migration не добавляет rootless sandbox, automated executor, Git publication, deployment execution, PROJECT skill authoring, parallel worktrees или remote control plane.
