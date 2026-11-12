# Готовые варианты решения вопросов

Задание пользователя: каждый вопрос/решение сразу сопровождается вариантами,
объяснением и рекомендацией; пользователь выбирает готовое либо пишет своё.
Никаких дополнительных confirmations. Сохраняется универсальность по проекту.

Allowed source changes перечислены в INPUT_BASELINE.json: local-web v4 schema,
prompt, normalization/choice validation, read-only interview/packet projection,
узкий answer POST через существующий public draft update/commit/recovery, UI/CSS
и build metadata. Core schemas/registries/state machines и CLI transport не
меняются. Версии v2/v3 и accepted history сохраняются. Options — предложения,
не доказанные факты/approvals. KEEP_OPEN подход не закрывает material gap.
Формальные Task/JIT/skills/unknowns не назначаются model choice effects.

Новый ответ хранится как digest-bound exchange record и включается в следующий
пакет. SET защищён от перезаписи изменённых после анализа данных, APPEND сохраняет
предыдущие ответы. Stale/source/replay/Origin/patch validation остаются. Никакой
mutation в GET/polling и никаких дополнительных model calls при выборе.

Tests: новый test_document_decision_options.py; только необходимые адаптации
старых fixtures/UI tests под новый envelope и custom-answer section. Новая
операторская глава 36, FILE_INDEX/manifests/mirror, wheel/frozen/installer;
новые evidence/CURRENT_TASK/packaging anchor. Предыдущие uncommitted изменения
сохранены. Целевые проверки: options/recommendation/typed changes, user/custom
answers, unresolved/future, replay/concurrent edits, recovery, legacy v2/v3,
real TCP/headless Edge и один actual CLI synthetic case. Full engine/core/PH-LW
matrix NOT RUN. Повтор только failed case или изменённая прямая зависимость.
Engine/Documentation delivery ZIP не создаются.
