# PH-051-06 — exact changed-file list относительно PH-051-05

**Version:** 0.5.1 WIP / NOT RELEASED. **Дата:** 2026-10-26.

Основание: байтовое SHA-256 сравнение с предоставленными Engine/Documentation PH-051-05 ZIP. Регистры, схемы, accepted reports, run history и Stage runtime вне scope не переписаны.

## Engine (изменено/добавлено файлов, кроме manifest и этого индекса: 40)

| Тип | Путь | SHA-256 предыдущее | SHA-256 новое |
|---|---|---|---|
| MODIFIED | `CHANGELOG.md` | `12f4323d9770f40199178400fda330e9307d0fa2a84c7c098d01c25d4a75a4f7` | `daf80eb84838502688ce03cc3b83d7d65c018f1903ea3424e45981240c72c6c3` |
| MODIFIED | `MANUAL_INSTALL.md` | `3be8641b3a3ea915758f2f413691be076e8fc19e1686bedf6508bbe27c88e6c7` | `7762c1fdb676aac0fd503e32bd34924ca3b4b87e83697ba671851f85c9265f77` |
| NEW | `PH_051_06_LOGS/DOC_VALIDATION.json` | `—` | `7b8864cc09f6d3d838f526bb64f953f2bd38118dddf6cc8464949402170dd4ee` |
| NEW | `PH_051_06_LOGS/DOC_VALIDATION.log` | `—` | `12cd7b0f3fa7787779604e524c1b3f6651812b1e0d7a8234fe68d6a25ff3aaae` |
| NEW | `PH_051_06_LOGS/PREFLIGHT.json` | `—` | `de23ce819e309b354b0a7cc8128141ad6994a2a6ea1de1588190a5592cc1ef33` |
| NEW | `PH_051_06_LOGS/PRESERVATION.json` | `—` | `bea0908df725684de0a2b2bb8b71e732f0f6998057505053bef9cdfee2f906b5` |
| NEW | `PH_051_06_LOGS/REGRESSION_FULL.exit` | `—` | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| NEW | `PH_051_06_LOGS/REGRESSION_FULL.log` | `—` | `a0daebf8419008e704fdb689871979cc0d3379b18ea9f9ca4ad78feb4f87653d` |
| NEW | `PH_051_06_LOGS/ROOTLESS_ENVIRONMENT.log` | `—` | `a9e092663ca3fd1b68c2e3cf908280f332346db6f9ff3060852f1d71664b897a` |
| NEW | `PH_051_06_LOGS/TARGETED_FINAL.log` | `—` | `407880a879108258e9de5f3b0a36513df7e20ea31f73a652f06c057f433015ec` |
| NEW | `PH_051_06_LOGS/WHEEL_BUILD.log` | `—` | `fcfc30dba7071cce5000d424f5a6dd7436a160cf6be14a03c34fb41312423cd3` |
| NEW | `PH_051_06_LOGS/WHEEL_DEMO.log` | `—` | `ec7dde592199581944ad04b979b76f82584d22e4539284be093a99f9c37f609d` |
| NEW | `PH_051_06_LOGS/WHEEL_INSTALL.log` | `—` | `d25c549b15fe59dc3ed7bfb09f236ed0b51c2b507b9b0753bf7ed1fcfb1386c6` |
| NEW | `PH_051_06_LOGS/WHEEL_NEXT.log` | `—` | `bb2f967d870946c068ed20cd08bdc2e8bb174f54b9d5940b0a4934cf2ddac0b7` |
| NEW | `PH_051_06_LOGS/WHEEL_SMOKE.log` | `—` | `d965bc8b327a05eacdd1fff4c2c4615ed16acf5150f03969f6b09c92abcc03ff` |
| NEW | `PH_051_06_LOGS/WHEEL_STAGE_STATUS.log` | `—` | `6c1e259f25d78a957167ddc651bf7f75f3a2591b52c6e732c57e3ab02ec0edc7` |
| NEW | `PH_051_06_LOGS/WHEEL_VALIDATE_HANDOFF.log` | `—` | `cb165144e67aff492cf2126b3dd659064547993df17e51877e0adcef9635c93d` |
| NEW | `PH_051_06_LOGS/WHEEL_VALIDATE_PROJECT.log` | `—` | `1522eeabe49afbce190c195b0de275c9439ddc177e1b60cb5853787c31c23c8f` |
| NEW | `PH_051_06_TEST_REPORT.md` | `—` | `04e60f9e0e2dfcb4457535516ff19319b12191600a619dfa26a489896c82fc68` |
| MODIFIED | `README.md` | `436a6fa696ee7ed5e99e44aaf7d315dc9d8dcbaa65a61c83b5ff5c9d54c39b16` | `4b0a6ef577c41c80148b16dec49b71ac8f87c433d797bc40ea79b3c9d5417656` |
| MODIFIED | `build/lib/project_harness/executors/codex_cli_local.py` | `eb68a578b308c7a5f558c0972462f0d0e5c291a1098750723b192a8f650d3d18` | `aac9aadc13f1f9c691e769d59bfc6890d6f13667767abbac4b5ed930d7a64de7` |
| MODIFIED | `build/lib/project_harness/executors/result.py` | `336b6c0f60481233734cbd9f402a10940f2d01555b9957d08dd180885021c6eb` | `e98b98a40d6af0aa4e04b4620168fc13a8d0e705914d04365ce8937c1371b5d1` |
| MODIFIED | `build/lib/project_harness/safety.py` | `8c483f2cf131c648edc70114265bc80d4313ed5b1b34ad952250f6ce2628a1b7` | `d82c75c80b0ba0358af43db21cce8e1b20128dcf06e5eb61afa9ba82039a3bfe` |
| MODIFIED | `build/lib/project_harness/sandbox/podman_rootless.py` | `a3ba6eb0a53ae05a49e81931ce0bf0b8914ab1289a1aa9bd28d61e267b728566` | `e784de4e057bacbbe562d3024b5147d7d41b0394930172db13be87b55f99b930` |
| MODIFIED | `dist/project_harness_engine-0.5.1-py3-none-any.whl` | `77475d5a08ab9d4c60cbbb113e354841b6a6f6afab54cff7b36ffa3cf60b015c` | `4b2b4587e6afe1e5da20c81bb5511c4a8a4f62a3258878e15e24d6ebc17cb985` |
| NEW | `docs/Project_Harness_Documentation_v0.5.1/05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md` | `—` | `08638bb9c78cc24d20194a16cdd8cdba9d4524b7b4bdc47d42cc6cfbb774d919` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/CHANGELOG.md` | `0debe2961cf9914526a6a3931245777156eb887a0929692c7c803ecfe2363755` | `33005036495825835cb3be8c223763025211d6eb259dda3fefa23858aa7087a1` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/FILE_INDEX.md` | `b05dc5f9fdbb5fae2d8bae939154f6dc7a22a38ed02fd49a8efae86fb9da75cb` | `4ff3f92e4ae47f67a514438e9a7a1476db26f380a4715c1ff5c83b2677964cbb` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/MANIFEST.sha256` | `775cbfec25caee9f8d8480872b5e1b28ee606d1df2b1e9adf92675fad7557dd5` | `ef63c9a29f6d943ce087f215614ce4fc69b1ba8c37016561e3ad1fc1fd7238d8` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/Project_Harness_Architecture_v0.5.0_FULL.md` | `32abf1817ef0d397fecbc7e7fd14a51d0982ff5c961dd25813671ba8446139ca` | `8af31fd195149f0ba65e1cd05861a4a1df6e163d8d5e11928f00ad80dcec45af` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/README.md` | `1fb1760d520697f7dc5df6534b2eed5768664cf065a9c34a5a3bdc4fc8eccc2e` | `3733dcec2b34e3f2f82376ee02b444ed55d5a1b4b831a53ac54ceaece0c272db` |
| MODIFIED | `docs/Project_Harness_Documentation_v0.5.1/VERSION.md` | `e993d371a60108294304118b74859900f4799c4473a92ee3480dcd4b40a03dad` | `c425aa2c977b3be1edc31c1caca30e88d40f58085d74aa4d9873e3a871565800` |
| MODIFIED | `src/project_harness/executors/codex_cli_local.py` | `eb68a578b308c7a5f558c0972462f0d0e5c291a1098750723b192a8f650d3d18` | `aac9aadc13f1f9c691e769d59bfc6890d6f13667767abbac4b5ed930d7a64de7` |
| MODIFIED | `src/project_harness/executors/result.py` | `336b6c0f60481233734cbd9f402a10940f2d01555b9957d08dd180885021c6eb` | `e98b98a40d6af0aa4e04b4620168fc13a8d0e705914d04365ce8937c1371b5d1` |
| MODIFIED | `src/project_harness/safety.py` | `8c483f2cf131c648edc70114265bc80d4313ed5b1b34ad952250f6ce2628a1b7` | `d82c75c80b0ba0358af43db21cce8e1b20128dcf06e5eb61afa9ba82039a3bfe` |
| MODIFIED | `src/project_harness/sandbox/podman_rootless.py` | `a3ba6eb0a53ae05a49e81931ce0bf0b8914ab1289a1aa9bd28d61e267b728566` | `e784de4e057bacbbe562d3024b5147d7d41b0394930172db13be87b55f99b930` |
| MODIFIED | `src/project_harness_engine.egg-info/PKG-INFO` | `bb21ff61c46eb3092e1fdc8bfc28e96e87c0630c3466810a909e9a79579f0129` | `ebf4afd24cb3c4d5b55737932b912103394190057deb21b3c5545554657af4aa` |
| MODIFIED | `src/project_harness_engine.egg-info/SOURCES.txt` | `f75bc85bc6554a657d99fc1a3b17ce91c7e9cef1194a2dfe24707fe8d6154767` | `61e15edc4c2c638266212351a6607a3d87f25d48508dbb2033207a19439fb966` |
| MODIFIED | `tests/test_ph_051_05_codex_adapter.py` | `3007f0bbaba6c707bcd120cc118b01398fcb8a7ccebc23a38433cc6b530897ca` | `2fd571a36221441653d52a7ecac990511baa5dda668283983b3e16b2e545a066` |
| NEW | `tests/test_ph_051_06_result_channel.py` | `—` | `eeadcfd95b27a966ef2e1b1501e2cc8e077fb7ad671e6dccc385eed587b3e640` |

## Documentation (изменено/добавлено файлов, кроме manifest: 6)

| Тип | Путь | SHA-256 предыдущее | SHA-256 новое |
|---|---|---|---|
| NEW | `05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md` | `—` | `08638bb9c78cc24d20194a16cdd8cdba9d4524b7b4bdc47d42cc6cfbb774d919` |
| MODIFIED | `CHANGELOG.md` | `0debe2961cf9914526a6a3931245777156eb887a0929692c7c803ecfe2363755` | `33005036495825835cb3be8c223763025211d6eb259dda3fefa23858aa7087a1` |
| MODIFIED | `FILE_INDEX.md` | `b05dc5f9fdbb5fae2d8bae939154f6dc7a22a38ed02fd49a8efae86fb9da75cb` | `4ff3f92e4ae47f67a514438e9a7a1476db26f380a4715c1ff5c83b2677964cbb` |
| MODIFIED | `Project_Harness_Architecture_v0.5.0_FULL.md` | `32abf1817ef0d397fecbc7e7fd14a51d0982ff5c961dd25813671ba8446139ca` | `8af31fd195149f0ba65e1cd05861a4a1df6e163d8d5e11928f00ad80dcec45af` |
| MODIFIED | `README.md` | `1fb1760d520697f7dc5df6534b2eed5768664cf065a9c34a5a3bdc4fc8eccc2e` | `3733dcec2b34e3f2f82376ee02b444ed55d5a1b4b831a53ac54ceaece0c272db` |
| MODIFIED | `VERSION.md` | `e993d371a60108294304118b74859900f4799c4473a92ee3480dcd4b40a03dad` | `c425aa2c977b3be1edc31c1caca30e88d40f58085d74aa4d9873e3a871565800` |

## Неизменность и packaging

В обоих архивах `MANIFEST.sha256` пересобран отдельно после окончательного freeze дерева, поэтому рекурсивный SHA для самого манифеста здесь не приводится.
Исходные PH-051-01–05 и PH-F01–F08 отчёты сохранены без изменений. По `PH_051_06_LOGS/PRESERVATION.json` 230 защищённых и внеобластных файлов точно совпадают с исходным PH-051-05 ZIP.
Отдельно пересобран wheel v0.5.1 и синхронизированы `src`, `build/lib` и embedded documentation. Документация дополнена PH-051-06 note, но существующие нормативные разделы не редактировались.
Реальный non-root Podman security acceptance **NOT RUN** — только условно применимые 2 теста пропущены; automatic release остаётся **NO-GO**.
