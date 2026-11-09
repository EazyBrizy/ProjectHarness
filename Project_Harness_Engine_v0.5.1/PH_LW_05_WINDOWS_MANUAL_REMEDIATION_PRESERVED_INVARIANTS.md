# Сохранённые инварианты — Windows manual remediation

- MANUAL_HANDOFF / network_mode NONE / null adapter and sandbox refs / EXPLICIT_AFTER_VERIFICATION сохраняются миграцией и проверяются tests.
- Accepted input, Stage/Run history и replay bytes неизменны; только kernel migration metadata обновляется штатным public API.
- Failed flush/copy до journal не меняет canonical root. Second rename failure возвращает старое дерево; real process exit до/после swap восстанавливается через public migrate-project.
- Read-only атрибут источника и внешнего hardlink не меняется cleanup. Удаляются только принадлежащие migration UUID siblings после native-path проверки.
- Public executor-doctor/execute-current на Windows BLOCKED; тест запрещает Popen и проверяет полный snapshot без mutation. No host Codex fallback, Podman install, policy/privilege changes.
- HTTP/service/import implementation и auth/CSRF/revision/replay contracts не менялись; повторные real TCP/Edge проверки проходят.
- Schemas, registries, templates, skills, нормативные specs и все прежние отчёты/logs сохранены. Зеркала docs/build/wheel проверяются отдельно; generated artifacts получены из canonical source.
- SKIP не означает security PASS; mixed automatic модули остаются FAIL. PH-LW-06 и полный manual release gate не объявлены выполненными.
