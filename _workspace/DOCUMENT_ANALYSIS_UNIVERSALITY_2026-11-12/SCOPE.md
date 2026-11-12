# Универсальность документального анализа

Задание пользователя: проверить отсутствие привязки к одному продукту/документам
и обеспечить общий анализ. Проверка охватывает MD/ZIP импорт, exact packet,
prompt, normalization, preview/saved answers и UI. Под «любой документацией»
понимается её содержание; поддержка PDF/DOCX/OCR не заявляется и в этот scope
не добавляется. Действуют существующие UTF-8 MD/ZIP, size/path/secret/policy limits.

Найдены: MIN_ANDROID_VERSION и предположение о прототипе в prompt; частный
template добавления technology.selections в форме; text_key стирает символы
языков C++/C# и регистр единиц; отсутствие явного состояния «план не описан».
Названия файлов, число 4, исходный продукт/его стек в runtime importer/exchange
не зашиты. Contract enums/refs/limits и текущий provisional GREENFIELD intake —
границы Harness, а не выведенные из документации факты; не выдавать их за
доказательство фактической зрелости описанного проекта.

Allowed source changes: пять файлов INPUT_BASELINE.json. Добавление readonly
core schema в interview projection для общего typed editor; core schema/registry,
execution и import policies не меняются. Tests: новый test_document_analysis_universality.py;
адаптация подписи кнопки, контекста question text и обращения по labels вместо
позиции полей в test_document_analysis_clarity.py под общий editor. Semantic
asserts версии/технологии сохраняются. Docs: новая глава 35 + generated FILE_INDEX/manifests/mirror; generated
wheel/frozen/installer; новый evidence/current navigation/packaging anchor.
Все предшествующие uncommitted изменения и отчёты сохраняются.

Целевые проверки: разные предметные области и 1/2/3/6 документов; разные имена,
порядок и вложенность; provenance/exact texts/пакет изоляция; отсутствие
навязанного стека/этапа; C++/C#/C, MB/Mb и Unicode; общий editor пользователей,
компонентов, критериев, технологий и enum по schema; пустой roadmap; preview
только текст и без auto-commit. Два actual native CLI cases на синтетических
документах разных типов. Остальное — declared fixtures, не оценка модели.
Full engine/core/PH-LW matrix NOT RUN. Повтор только после изменённой зависимости
или конкретного failure. Engine/Documentation delivery ZIP не собирать.
