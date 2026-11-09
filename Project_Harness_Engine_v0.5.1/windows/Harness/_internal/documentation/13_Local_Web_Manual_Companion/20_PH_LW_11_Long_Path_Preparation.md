# PH-LW-11 — подготовка проекта с длинными Windows paths

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-08  

Дополнение по отдельному заданию исправляет прежний long-path FAIL подготовки. Фактические команды, build hashes и verdict находятся в `PH_LW_11_LONG_PATH_TEST_REPORT.md` Engine. Прежний `PH_LW_11_TEST_REPORT.md` и исходный FAIL сохранены как история. Полная PH-LW-11 acceptance и Local Web manual release по-прежнему требуют отдельных mandatory environments; PH-LW-12 этим дополнением не выполняется.

## Поведение и граница

В Local Web подтверждается обычная новая локальная папка проекта. Подготовка остаётся manual: отдельные approvals → public `prepare_handoff` → проверка directory/ZIP/manifest/first JIT → native no-replace publication. Она не меняет принятый scope, уровни, refs, доказательства или состояния ядра.

Для файлового IO Windows используются внутренние extended drive paths после проверки обычного пути. Эта форма не является новым видом пользовательского ввода: UNC, device namespace, drive-relative roots, ADS, junction/symlink ancestors и недопустимые компоненты остаются запрещены. Публичные paths, relative refs, manifests, operation records и UI не получают extended prefix. Системные настройки, включая LongPathsEnabled, не меняются.

Копирование всего дерева недостаточно: traversal, чтение schemas/registries/JIT, хеширование manifest и protected phase boundary должны видеть длинные файлы. Отсутствующий или изменённый файл сохраняет прежний FAIL. IO-преобразование не даёт права пропускать validation checks или повторять committed операции.

После прерывания публикации используйте существующую явную recovery action. Подтверждённые directory identity, exact input binding и artifact digests проверяются повторно; compiler не запускается заново после подтверждённого rename. Чужие и уже существующие папки не перезаписываются. Closing/reopening browser по-прежнему не отменяет mutation.

Automatic executor остаётся выключен. Self-contained installer не превращается в Python interpreter продуктовых команд. Реальная подпись не добавлялась; комплект без signing credentials остаётся UNSIGNED. Engine/Documentation ZIP этим заданием не создаются.
