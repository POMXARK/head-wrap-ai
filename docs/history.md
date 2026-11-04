# История работы над головой: от видов Qwen до исправления

Собрано из git corsairs-remake (`journal_import.py`) в `journal/steps.jsonl`; здесь — читаемая сводка по фазам. Коммит = действие, тема коммита = что сделано. Вердикт по коммиту неизвестен (`unknown`), кроме откатов (`deadend`).

Чего в журнале нет: промпты и запуски в чате и ComfyUI, которые не попали в коммиты (какие именно сиды/варианты пробовались, оценки «на глаз» пользователя). Это надо писать в журнал при каждом запуске (`journal.py add`).


## 1. Виды Qwen (Qwen Image 2.1 edit: четыре ортогональных вида головы/персонажа)
2026-10-23 … 2026-11-02, 8 шагов

- 2026-10-23 `ef465c4` feat: pdm_comfy_refine_graph.py builds the API graph of the Qwen Image 2.1 edit template
- 2026-11-02 `240c6e2` feat: Pixal3D 4-view workflow with Qwen refine step
- 2026-11-02 `dbc7ac8` fix: describe hands in the Qwen refine prompt
- 2026-11-02 `62cd401` fix: keep T-pose arms in side views of the Qwen refine prompt
- 2026-11-02 `aa6c264` feat: parts workflow — one Qwen pass on a 2x2 sheet of the views
- 2026-11-02 `bbe292c` feat: parts texture follows the Qwen views, 4x upscale, realistic skin prompt
- 2026-11-02 `7e4874f` fix: parts workflow — QwenVL gives at most 25 tags
- 2026-11-02 `951567b` fix: parts workflow — view tags by the local Qwen3.5-9B, no download

## 2. Подготовка видов (despill зелёного фона, выравнивание боковых видов по фронту и ушам)
2026-11-02 … 2026-11-03, 8 шагов

- 2026-11-02 `d950a06` fix: part views on a green background
- 2026-11-02 `fb05ae8` fix: parts workflow — despill green rim, cap TextGenerate length
- 2026-11-02 `3ef660a` feat: views aligned to the mesh by optical flow before the projection
- 2026-11-02 `1c4fe3e` feat: PDMPartSave also saves the projection without alignment
- 2026-11-03 `513c122` feat: despill green screen from the head view
- 2026-11-03 `deb1ddb` feat: align side head views to the front proportions before Pixal3D
- 2026-11-03 `cc29c4e` feat: align the back head view to the front by the ears
- 2026-11-03 `e0a5a31` feat: match head view widths in align_views

## 3. Создание модели (Pixal3D/TRELLIS, графы ComfyUI, разбиение на части)
2026-10-23 … 2026-11-03, 30 шагов

- 2026-10-23 `024c78f` feat: PixelArtistry watertight workflows through the API converter
- 2026-11-02 `f8e6884` feat: ComfyUI workflow for Pixal3D Multiview from 4 ready views
- 2026-11-02 `16bcf5f` feat: ComfyUI workflow that splits a character into parts by itself
- 2026-11-02 `4f00ff7` fix: parts workflow — no invented details in prompts, front as reference, optimize not fatal
- 2026-11-02 `481c6aa` feat: parts workflow lets the VLM write the prompt of every view
- 2026-11-02 `235c405` fix: parts workflow — decimate to 60000 faces before the UV unwrap
- 2026-11-02 `2934d2f` fix: parts workflow — refine_prompt off by default
- 2026-11-02 `77fcefa` fix: parts workflow — back view without the front reference
- 2026-11-02 `88179c7` feat: parts workflow — silhouette mask from the render instead of background removal
- 2026-11-02 `d454484` fix: parts workflow — back to background removal, smooth outline in prompts
- 2026-11-02 `32b6220` fix: parts workflow — ears and mouth in the head prompt, adaptive unwrap
- 2026-11-02 `7d0d23d` fix: parts workflow — patch flash_attention_decode_gqa so refine_prompt works, keep ponytail, matte light
- 2026-11-02 `99f11c2` fix: parts workflow — TextGenerate max_length 4096, 400 broke the sheet
- 2026-11-02 `e23393d` fix: parts workflow — refine_prompt off again, shorter skin phrase, 20 steps
- 2026-11-02 `e5a8154` fix: parts workflow — head prompt states the ponytail explicitly
- 2026-11-02 `710fb62` feat: parts workflow — the enhancer lists the key details itself (up to 50)
- 2026-11-02 `4fcbb8e` fix: parts workflow — back to the prompt of the good sheet, show the sheet prompt
- 2026-11-02 `0ab5a9a` feat: parts workflow — VLM tags of the sheet join the prompt
- 2026-11-02 `7c6502a` feat: parts workflow — tags per view, joined by cell into the sheet prompt
- 2026-11-02 `b4116e3` feat: parts workflow — previews of the sheet before the cut
- 2026-11-02 `76c0b9d` fix: parts workflow — tags prompt of a single view does not mention the grid
- 2026-11-03 `9aa635c` fix: parts workflow — remesh drops the inner UDF shell, smoothing 20 -> 3
- 2026-11-03 `f5ce2f7` fix: parts workflow — solid remesh instead of the double-walled UDF shell, random Pixal3D seeds
- 2026-11-03 `97be7a8` fix: parts workflow — solid remesh with fill 0, the head was still hollow
- 2026-11-03 `20b6940` feat: head graph from the official Pixal3D template
- 2026-11-03 `aa1e710` feat: two-view (front+back) Pixal3D head graph
- 2026-11-03 `e5e343c` feat: bf16 variants of the Pixal3D head graphs
- 2026-11-03 `0d4e747` fix: four-view head graph instead of front+back
- 2026-11-03 `dc89efd` chore: record the ear defect of the 4-view Pixal3D head
- 2026-11-03 `847379b` docs: bf16 Pixal3D crash on 16 GB VRAM and the launch flags for it

## 4. Сплошное тело (двойная поверхность, ремеш)
2026-11-03 … 2026-11-03, 3 шагов

- 2026-11-03 `e43633c` chore: notes — ComfyUI_00016 is a clean closed mesh after the solid remesh
- 2026-11-03 `dffbc2f` feat: rebuild generated heads as one solid wall before painting from the views
- 2026-11-03 `3d29ef8` feat: voxel remesh of a head in 3DCoat from the console

## 5. Развёртка UV (3DCoat, швы, оценка)
2026-11-02 … 2026-11-04, 10 шагов

- 2026-11-02 `8384ab6` fix: views levelled in tone before blending — seams on the nose, ear and neck
- 2026-11-03 `ab42ba9` feat: mesh cleanup and new unwrap before the projection of the views
- 2026-11-03 `b87d406` feat: view-based UV atlas (10 charts) for generated heads
- 2026-11-03 `c899935` feat: 3DCoat UV from the console, rule-based head seams and a UV run scorer
- 2026-11-03 `fc46dfc` feat: 10k-face hero1 head from painted2 with 3DCoat UV
- 2026-11-03 `74f8106` feat: head parts, region tools, learning agent, GUI and UV unfold for hero1
- 2026-11-03 `2ea8d81` feat: open copies of 3DCoat tools, measured by a black-box probe
- 2026-11-03 `7e4965f` feat: start 3DCoat minimized in coat_run.sh
- 2026-11-03 `cfcca6c` feat: open copies of ABF, pack, weld, reduce, relaxSurface and Auto Seams islands of 3DCoat
- 2026-11-04 `7998225` feat: run 3DCoat on a hidden desktop, tune uv_unfold (ARAP, square pack), overlap-aware uv_score

## 6. Текстура по видам (проекция, выравнивание тона, видимость)
2026-10-23 … 2026-11-04, 19 шагов

- 2026-10-23 `84d5c19` feat: comfy_view_refine.py redraws model views through ComfyUI before the 3D step
- 2026-10-23 `38779b7` fix: take views_refined only when it holds the views of these names
- 2026-11-01 `04c9d95` feat: pdm_model_views --tpose, arms raised for image-to-3D
- 2026-11-02 `64a107a` feat: paint the part texture from the four views
- 2026-11-02 `a1bd5eb` fix: view projection — visibility, sharp view weights, rim of the views skipped
- 2026-11-02 `875d3c6` fix: mesh smoothed before the projection, texels without a view in the tone of their neighbours
- 2026-11-02 `42394be` fix: tone levelled by the views that face the texel, wider blur
- 2026-11-03 `84edc37` fix: view weight follows the neighbour-averaged normal, no more patches on the face
- 2026-11-03 `89a792f` fix: projected GLB gets smooth vertex normals
- 2026-11-03 `9a1c2a1` fix: pdm_project_views.py — faces without a view blended per texel (IDW), not one flat colour per face
- 2026-11-03 `dc4cbe7` fix: pdm_project_views.py — fill every face with weak view coverage from its neighbours in space
- 2026-11-03 `359dbc4` fix: pdm_project_views.py — BAD_SHARE constant for weakly covered faces
- 2026-11-03 `5e86eb1` fix: view projection — the pupil is not background, the view weight has no cap
- 2026-11-03 `e01d0b7` fix: drop stale TRELLIS PBR maps from projected head
- 2026-11-03 `3103bfa` feat: match head view outlines row by row and the neck of the back
- 2026-11-03 `cd0deb7` perf: compile view projection rasterizers with numba, level tone in 3D
- 2026-11-03 `ec0097b` fix: weight view projection by depth facing and occlusion, fill unseen texels in 3D
- 2026-11-03 `0c3ee41` docs: how to fix a generated head, view source map
- 2026-11-04 `37dd20a` feat: twelve-view check of the head against the original and autonomous fixing

## 7. Проверка и правка (head_check, части, инструменты, агент)
2026-11-03 … 2026-11-03, 1 шагов

- 2026-11-03 `d134692` feat: head checker, fix driver and the skin guard for generated heads

## Откаты (тупики)
2026-11-02 … 2026-11-02, 1 шагов

- 2026-11-02 `b7c9898` Revert "feat: parts workflow — silhouette mask from the render instead of background removal"

## Документация
2026-11-03 … 2026-11-04, 5 шагов

- 2026-11-03 `bedbd0d` docs: inverted faces were the main cause of side artefacts
- 2026-11-03 `5ee4921` docs: analysis of v9 head screenshots and the measures taken
- 2026-11-03 `bd0ef35` docs: head 3D research backlog pointer
- 2026-11-03 `cb90f95` docs: model3d README — head research backlog section
- 2026-11-04 `15fed21` docs: pointer to head-wrap-ai plan and the list of head defects

## Заметки
2026-11-03 … 2026-11-03, 2 шагов

- 2026-11-03 `3c1a759` chore: REACH named constant, tighter z-check tried and kept at 5 %
- 2026-11-03 `04942f5` chore: notes — RTX 5080 power limit and reserved VRAM for ComfyUI

## Прочее
2026-10-21 … 2026-11-04, 11 шагов

- 2026-10-21 `8179620` feat: Escape opens the game menu, voice-over and 3D model tools, walk fixes in town
- 2026-10-23 `153e881` feat: pdm_models_all.py runs the whole model chain for many models
- 2026-10-23 `ee085e2` fix: pdm_models_all.py steps and the interpreter of the steps
- 2026-10-23 `70383c2` feat: characters part by part (--parts) to keep hands off the coat and the blade
- 2026-10-23 `4d7cc83` feat: --only-parts, build a character from the good parts only
- 2026-10-23 `058222e` fix: parts of hero and the other figures with the 17 objects of hero1
- 2026-11-01 `c07714c` feat: pdm_models_all --tpose
- 2026-11-02 `a9ba41c` feat: parts save — install missing optimizer packages by itself
- 2026-11-02 `812495d` feat: glb optimizer — drop specks and Taubin-smooth the decimated mesh; no eye catchlight
- 2026-11-02 `99d0bea` feat: PDMPartSave copies the painted GLB next to the raw one
- 2026-11-04 `b4a8ac8` perf: repaint 21.6 -> 9.4 s, parallel tries in head_auto

## Складка под глазом (воронка глазницы)
- `fold_probe.py [glb] [eye_open.json]` — анализатор без запуска игры: профиль z и нормалей через центр глаза, число острых рёбер под глазом, карта глубины `fold_profile.png`.
- Причина складки: у обёрнутой головы вокруг глаза воронка с плоским дном (z 0,279 против щеки 0,326) и стенкой с перевёрнутыми нормалями.
- `export.py smooth_pits` выравнивает воронку точным решением Лапласа (флаг `--no-fold` отключает), `under_eye_mask` закрашивает кожей текстуру под глазом; шаг входит в `headwrap.build()`.
- Проверка анализатором: плита 0,319 вместо 0,28, без перевёрнутой стенки; в игре дуги и эллипсов нет, моргание работает.

## Оценка глаз по мешам без игры (eye_score.py)
- `eye_score.py glb eye_open.json [--png] [--json]` рендерит z-буфером голову с патчами глаз (виды 0/±25°) и считает: visible (патч не закрыт головой), through (просвет на фон), aperture (раскрытие h/w, цель 0.27–0.45), back (перевёрнутые грани), step (ступенька кромки), shade, depth, gaps (дыры), blocky (кубики текстуры). Итог `score N/100`, код выхода 1 при провале. Шаг входит в `headwrap.build()` как предупреждение.
- Складка/воронка: `smooth_pits` (точное решение Лапласа по воронке + PIT_RINGS колец кромки), перевёрнутые грани воронки разворачиваются к фронту, `fit_uv` перефитывает UV воронки, текстура под глазом — LaMa с растушёванным краем.
- Раскрытие: SHRINK (0.97, 0.8), LOW 0.55 → aperture 0.27 (проходит порог). Значения 0.9/0.8 ломают контур дыры (вырожденный патч) — не повышать.
- Известно (не решено): на ±25° aperture шумит, остаются кубики текстуры (blocky 0.6–0.75), небольшая прореха у внутреннего угла правого глаза; score 70/100.
- Проверено в игре (тест eye-blink): глаз с радужкой, без полукруга, error.log пуст.

## Почему глаза не раскрывались (проверено измерением, 2026-11-04)
- Раскрытие (h/w) патча 0.26 при полигоне 0.34 — из-за `SHRINK` y 0.8 и `LOW` 0.55 в `eye_slit.py`; оба вручную поднимались и ломали глаз.
- Дыра каждого глаза — **не одна петля**: 3–5 несвязных компонентов удалённых граней (воронка шаблона = стопка слоёв щека/стенка/дно, до выравнивания на разных z; плюс островки). `hole_loops` отдавал по петле на компонент.
- Прежний код брал одну петлю (`loop[0]`, потом самую широкую) → при росте дыры патч закрывал только часть, остальное — сквозная чёрная прореха («глаз сломался», чёрный/бирюзовый глаз), либо вырожденный патч (`zero-size array`).
- Исправлено: `eye_slit.fill_islands` (грани с ≥2 удалёнными соседями удаляются), патч строится на **каждой внешней петле** (не лежащей внутри более широкой), нормали кромки ориентируются к фронту. Параметры: `SHRINK=(0.97,0.9)`, `LOW=0.8` → aperture R 0.30, L 0.34, visible 0.91; оба глаза с радужкой, в игре `error.log` пуст.
- Осталось: на R светлая дуга по границе перефита UV, шум aperture на ±25°, кубики текстуры (blocky 0.6–0.75). Score 68/100.
