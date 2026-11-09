# Ранняя одиночная диагностика PH-LW-09

До финальных acceptance runs был отдельно запущен `tests.test_ph_lw_09_tasks.TaskConsoleTests.test_read_only_refs_current_stage_and_exact_prompt` через `.venv/Scripts/python.exe -B -m unittest -v` из workspace. Exit 1, ERROR: Windows native-path preflight ожидал обычный каталог, ему передавался файл canonical artifact. Исправлено на проверку родительского каталога с отдельными проверками файла.

Отдельный raw stdout этой короткой диагностики не сохранён на диск: вывод остался в transcript инструментального вызова. Это ограничение ранней диагностической записи, не acceptance evidence. Та же причина зафиксирована в сохранённом `runs/target-initial.log`; окончательные target/native/wheel прогоны имеют полные logs и run metadata. Никакой PASS по несохранённому выводу не засчитан.
