# PH-LW-06: фактические доказательства

`regressions-final` — все 40 модулей заново на финальном коде; прежние результаты не подставлены.
`native-final` — Windows/NTFS/non-admin/CPython 3.14, pinned Flask/Waitress, реальный TCP и Edge.
64 runtime tests и doctor PASS; общий wrapper FAIL из-за двух ошибок оформления docs.
`docs-corrected` — отдельный успешный retest после исправления docs; `NATIVE_SCOPE_VERDICT`
связывает эти два прогона, не переписывая исходный FAIL и не объявляя повтор 64 методов.
`runs/installed-wheel-final` — отдельная venv и Unicode CWD; импорт только из установленного wheel.
`target-sixth` — последний предварительный run (15 exchange + 4 HTTP methods); финальные native,
regression и installed-wheel runs включают дополнительный шестнадцатый exchange test.
Ранние FAIL, промежуточные wheel builds и диагностические browser runs сохранены, а не объявлены PASS.
`browser-visual` — проверенные снимки UI из предварительного успешного run, данные полностью синтетические.

Raw evidence остаётся в `_scratch/ph_lw_06`. В опубликованных текстах заменены пользовательские
пути/bootstrap values существующим sanitizer. EVIDENCE_INDEX различает raw и published SHA-256;
вложенные log hashes в скопированных run.json относятся к raw bytes. Ни uploads/auth,
ни временные projects, ни venv/wheelhouse в evidence не включены.

SKIP не является PASS; failure/error events включают subtests и не дают число успешных methods
простым вычитанием. Seven mixed Linux/automatic module FAIL сохранены в общей матрице.
Source tests, installed wheel и финальная проверка рабочих файлов — разные evidence runs.
ZIP-пара не создавалась по новому правилу пользователя; финальные hashes рабочих деревьев
находятся отдельно в `_workspace/PH_LW_06`, вне самих хешируемых деревьев.
