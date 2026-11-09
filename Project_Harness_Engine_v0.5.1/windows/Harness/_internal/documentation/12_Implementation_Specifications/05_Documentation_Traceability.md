# Трассировка задач и изменений к документации

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Каждая задача должна явно знать:

- к какому пользовательскому outcome относится;
- какие requirements, constraints и decisions реализует;
- какие документы и разделы являются её входом;
- какую документацию она обязана изменить;
- почему документация не меняется, если это действительно не требуется.

Документация является частью результата разработки, но не каждая мелкая операция требует нового документа или ADR.

## 2. Двойная ссылка

Каждая значимая ссылка включает:

1. устойчивую canonical entity;
2. человекочитаемое расположение документа.

```yaml
documentation_ref:
  entity_ref: REQ-AUTH-001
  document: docs/requirements/authentication.md
  section_id: auth-login
  heading_hint: "Вход пользователя"
  revision: 4
  content_hash: sha256:...
  relation: SOURCE
```

`heading_hint` предназначен только для отображения. Стабильным идентификатором является `section_id` или explicit anchor.

## 3. Documentation Impact

```text
NONE
UPDATE_EXISTING
CREATE_NEW
SUPERSEDE
GENERATED_ONLY
```

| Значение | Когда использовать |
|---|---|
| `NONE` | Поведение, интерфейсы и принятые решения не изменяются. Требуется rationale. |
| `UPDATE_EXISTING` | Меняется существующее документированное поведение. |
| `CREATE_NEW` | Возникает новый публичный контракт, workflow или material concept. |
| `SUPERSEDE` | Старый документ/раздел становится историческим и заменяется новым. |
| `GENERATED_ONLY` | Изменяется только generated view, исходные canonical entities уже обновлены. |

## 4. Поля Task Contract

```yaml
documentation:
  source_refs:
    - entity_ref: REQ-SEARCH-001
      document: docs/requirements/search.md
      section_id: search-by-name
      revision: 2
      content_hash: sha256:...

  decision_refs:
    - entity_ref: ADR-API-004
      document: docs/architecture/adr/004-search-api.md
      section_id: decision
      revision: 1

  impact: UPDATE_EXISTING
  required_updates:
    - document: docs/api/search.md
      section_id: endpoint-search
      reason: "Добавляется параметр query"
      owner: TSK-BE-SEARCH-030

  generated_views:
    - STATUS.md
    - .harness/generated/requirements-coverage.md

  not_applicable_reason: null
```

## 5. Documentation gate

Task не может перейти в `DONE`, пока не выполнено одно из условий:

- required documentation updates applied and validated;
- documentation impact `NONE` с непустым rationale;
- documentation work вынесена в зависимую task, которая является mandatory частью того же Work Package;
- documentation intentionally deferred через approved decision/waiver.

Нельзя помечать `NONE` автоматически только потому, что agent не изменил Markdown.

## 6. Source precedence

Для реализации используется порядок:

```text
Accepted canonical entity
→ accepted ADR/Decision
→ accepted human-readable document section
→ generated view
→ current implementation evidence
→ untrusted source
```

Если код расходится с accepted requirement, это не означает автоматическое изменение requirement. Brownfield reconciliation определяет, является ли код фактическим baseline или дефектом.

## 7. Update workflow

```text
1. Resolve task documentation source refs.
2. Verify document revision/hash.
3. Detect documentation impact before execution.
4. Add documentation changes to write scope.
5. Execute product change.
6. Update canonical entities first when semantics changed.
7. Update human-readable documents.
8. Regenerate derived views.
9. Validate links, anchors, examples and contract consistency.
10. Record changed/superseded refs in Task Report and Result Envelope.
```

## 8. Stable section identifiers

Рекомендуемый Markdown-формат:

```markdown
<a id="auth-login"></a>
## Вход пользователя
```

или front matter registry:

```yaml
sections:
  auth-login:
    heading: "Вход пользователя"
```

Validation tool должен обнаруживать:

- missing anchor;
- duplicate section ID;
- stale revision/hash;
- ссылка на superseded document;
- required update без task owner;
- changed public interface без documentation impact.

## 9. Документация разных типов задач

| Task type | Ожидаемый documentation impact |
|---|---|
| Новая публичная API-функция | `UPDATE_EXISTING` или `CREATE_NEW` |
| Внутренний refactoring без изменения поведения | Обычно `NONE` с rationale |
| Architecture decision | `CREATE_NEW` ADR и обновление architecture baseline |
| Bug fix, возвращающий documented behavior | Обычно `NONE` или update known-issues/changelog |
| Изменение documented behavior | `UPDATE_EXISTING` + requirement/decision change |
| Directory/bootstrap | `GENERATED_ONLY` или update project layout docs |
| Test-only task | `NONE`, если behavior не меняется |
| Skill/prompt maintenance | Update control-plane documentation and registry |

## 10. Task Report fragment

```yaml
documentation_result:
  status: UPDATED
  source_refs_verified: true
  updated:
    - entity_ref: DOC-API-SEARCH
      previous_revision: 2
      resulting_revision: 3
      path: docs/api/search.md
      sections: [endpoint-search]
  created: []
  superseded: []
  generated_views_refreshed:
    - .harness/generated/requirements-coverage.md
  validation_evidence_refs:
    - EVD-DOC-LINKS-001
    - EVD-DOC-CONTRACT-002
```

## 11. Documentation ownership при параллельной работе

Разделы документации имеют read/write sets, как код и contracts.

```yaml
documentation_access:
  read:
    - docs/api/search.md#endpoint-search
  write:
    - docs/implementation/backend-search.md
```

Две parallel tasks могут читать один раздел. Одновременная запись в один section ID запрещена без explicit merge owner.

## 12. Критерии приёмки

1. Каждая executable task имеет `documentation` block.
2. Source refs включают canonical entity и document section.
3. Public behavior change не может завершиться с impact `NONE`.
4. Documentation gate входит в Task completion.
5. Broken/stale anchors выявляются автоматически.
6. Result Envelope показывает, что обновлено, создано или superseded.
7. Parallel planner учитывает documentation write conflicts.
8. Generated views не становятся canonical source of truth.
