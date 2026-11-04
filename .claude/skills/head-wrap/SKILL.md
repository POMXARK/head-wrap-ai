---
name: head-wrap
description: Запустить или пересобрать конвейер head-wrap-ai после обтяжки шаблона головы — текстура (цвет как в оригинале, чистка шеи, паддинг швов, LaMa по швам и пятнам), сборка glb с глазами и хвостом, установка в игру (hero и hero1) и рендер видов. Использовать, когда нужно обновить голову героя в игре, пересобрать текстуру после правки любого шага или проверить, каких файлов конвейеру не хватает.
---

# Конвейер head-wrap-ai

Один вход: `cd $W/head-wrap-ai && python3 headwrap.py <команда>` (`W=/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux`). Подробности и причины каждого шага — `docs/plan.md`.

## Команды
- `status` — какие файлы `work/` есть (`MISS` — шаг ещё не сделан) и стоит ли LaMa (`$W/lama/big-lama.pt`).
- `texture [--from N]` — baked27 → colormatch → cleanneck → padedge → lama_seam → lama_patch → padedge → baked29. Шаг пропускается, если его выход новее входов; `--from N` (0…5) принудительно с N-го шага.
- `build` — `export.py`: голова + глаза-шары (щель) + хвост → `work/hero1_eye.glb`.
- `game [--model hero]` — копирует glb в `glb_wrap/{hero1,hero}_head.glb`, `pdm_glb2gm.py … --only-parts head`, рендер видов в `/tmp/hv_<model>/<model>_{front,left,right,back}.png`.
- `all` — texture + build + game.

## Порядок и ловушки
- Паддинг (`padedge`) обязателен перед LaMa: иначе LaMa берёт контекст из чёрного фона и шов темнеет; после LaMa — паддинг снова.
- LaMa — открытая нейросеть (CPU, веса и пакет в `$W/lama`, не в git). Прямоугольники `PATCHES` в `headwrap.py` — координаты блока под губой именно этой головы; для другой головы перепроверить на текстуре.
- Движок отсекает грани по обмотке: после правок сетки объём каждой детали (trimesh `volume`) должен быть > 0.
- Не запускать вторую копию игры (FPS 0); живую проверку — `pdm-game/live.sh start|snap|stop` (см. skill head-wrap-check).
- Конвертеры игры идемпотентны; `pdm_glb2gm.py` без `--only-parts head` перезапишет остальные части.

## После правки
Смотреть рендер (skill head-wrap-check), `journal.py add "<что и результат>"`, коммит по правилам проекта (английский, `feat:/fix:`, `Tests:`), push; запись в `docs/plan.md` до коммита.
