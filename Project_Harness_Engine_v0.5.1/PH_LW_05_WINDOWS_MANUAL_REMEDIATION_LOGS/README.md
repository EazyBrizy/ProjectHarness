# Windows manual remediation evidence

Исходные runs сохранены в workspace `_scratch/manual-remediation`. Здесь заменены пути пользователя, workspace/temp и bootstrap values; EVIDENCE_INDEX хранит raw/published hashes отдельно. Хеши внутри скопированных run.json относятся к исходным raw logs.

REGRESSION_MATRIX_CURRENT — свежие 18 модулей; COMBINED — 38 модулей с явной provenance: 20 прежних результатов не прогонялись заново. Failure/error events могут быть subtests, поэтому их сумма не равна числу отдельных test methods. SKIP не считается PASS. Ранние воспроизведения дефектов и промежуточные builds сохранены; final installed-wheel run заменяет candidate run. Полная финальная пара проверяется отдельно после упаковки, attestations лежат рядом с ZIP.
