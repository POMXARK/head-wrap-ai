/* Интерактивный гайд head-wrap-ai (наш). Подключается сервером ко всем страницам (app.py: send → <script src="/tour.js">).
   Кнопка «? Гайд» внизу слева открывает меню: гайд по этому окну или по всем окнам подряд.
   Шаг: {sel, t, x, pre(), wait:{sel,ev}|cond(), pos}. Подсвеченное место остаётся доступным для мыши: можно сразу попробовать.
   Данные о пройденном — localStorage (необязательно, везде try/catch). Клавиши: → / Enter далее, ← назад, Esc закрыть. */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var click = function (s) { var e = $(s); if (e) e.click(); };
  var hasG = function (n) { try { return typeof (0, eval)(n) !== 'undefined'; } catch (e) { return false; } };
  var G = function (n) { try { return (0, eval)(n); } catch (e) { return undefined; } };
  var call = function (f) { try { var g = window[f]; if (typeof g === 'function') return g.apply(null, [].slice.call(arguments, 1)); } catch (e) {} };

  /* окна и порядок прохождения «всех окон» */
  var PAGES = [
    ['/', 'Главная: профили оценщика'],
    ['/pipeline', 'Конвейер: собрать и оценить голову'],
    ['/edit', 'Редактирование: форма, текстура, UV'],
    ['/review', 'Сравнение вариантов A/B'],
    ['/proto', 'Прототипы (макеты)']
  ];

  var TOURS = {};
  TOURS['/'] = [
    { t: 'Главная страница', x: 'Отсюда открываются все окна. Здесь же настраивается <b>оценщик</b> — модель-помощник, которая сравнивает варианты. Если вы не пользуетесь оценщиком, сразу идите в «Конвейер».' },
    { sel: '#h-go', t: 'Что вы хотите сделать?', x: 'Четыре карточки ниже — четыре задачи. <b>Собрать голову</b> — окно «Конвейер». <b>Поправить форму или текстуру</b> — «Редактирование». <b>Заменить части</b> — «Модель». <b>Сравнить варианты</b> — «Сравнение». Те же окна — в шапке.' },
    { sel: '#pr', t: 'Профили моделей', x: 'Каждая карточка — один оценщик: название, тип (Ollama или OpenAI-совместимый), адрес и модель. «Используется» выбирает активный. «Проверить связь» показывает «✓ Связь есть» или причину ошибки. Без оценщика остальное работает.' },
    { sel: '#bsave', t: 'Сохранить', x: 'Серая, пока ничего не менялось. После правки профиля становится доступной — без неё изменения не сохранятся (страница предупредит при уходе). «+ Добавить профиль» создаёт новую карточку.' },
    { sel: '#lg', pre: function () { var d = $('#lg').closest('details'); if (d) d.open = true; }, t: 'Журнал сервера', x: 'Что делал сервер: проверки, запросы к оценщику. Обновляется сам раз в 2 секунды.' }
  ];

  TOURS['/pipeline'] = [
    { t: 'Конвейер головы', x: 'Окно собирает голову героя для игры и показывает, хорошо ли получилось. Порядок: <b>настроить → собрать → посмотреть оценку → при желании положить в игру</b>. Каждый шаг можно повторить.' },
    { sel: '#pill', t: 'Что происходит сейчас', x: 'Плашка показывает состояние: «Ожидание», «Идёт: …», «Готово» или «Ошибка, код». Пока шаг идёт, другие кнопки недоступны.' },
    { sel: '#b-build', t: '1. Собрать голову', x: 'Главная кнопка. Строит модель и сразу оценивает её. Если сомневаетесь в настройках — оставьте умолчания и нажмите её.' },
    { sel: '#b-texture', t: 'Пересобрать текстуру', x: 'Нужна, если меняли сглаживание под челюстью. Идёт долго — запускайте и занимайтесь другим.' },
    { sel: '#b-eyes', t: '2. Оценка', x: '«Оценить глаза» проверяет, видны ли они и раскрыты ли. «Оценить сетку» ищет осколки и растянутую текстуру. «Проверить файлы» показывает, каких файлов шагов не хватает.' },
    { sel: '#b-game', t: '3. Положить в игру (опасно)', x: 'Перезаписывает файлы игры. Перед этим всегда спросит подтверждение и скажет, что будет перезаписано. «Всё сразу» делает сборку, запись и проверку подряд. Модель (hero или hero1) выбирается выше.' },
    { sel: '.vbox', t: 'Модель', x: 'Собранная голова в 3D. Мышь: вращать, колесо — масштаб. Если область пустая — модель ещё не собрана.' },
    { sel: '.cmp', t: 'Сравнить с вариантом', x: 'Выберите слева и справа два варианта (или «текущая сборка»), чтобы увидеть их рядом.' },
    { sel: '#tb-res', t: 'Оценка', pre: function () { call('tab', 'res'); }, x: 'Баллы по глазам и сетке с картинками. «⚠ оценка устарела» значит, что голову пересобрали после оценки — оцените заново.' },
    { sel: '#tb-opt', t: 'Настройки', pre: function () { call('tab', 'opt'); }, x: 'Параметры сборки. Если сомневаетесь, не трогайте. Изменили — сохраните и пересоберите голову.' },
    { sel: '#tb-var', t: 'Варианты', pre: function () { call('tab', 'var'); }, x: 'Сохраните текущую сборку под именем вместе с настройками и баллами, чтобы сравнивать несколько вариантов. Первым сохраните «умолчания» как точку отсчёта.' },
    { sel: '#tb-log', t: 'Журнал', pre: function () { call('tab', 'log'); }, x: 'Живой вывод запущенного шага. Здесь видно, на каком месте остановилось, если была ошибка.' },
    { sel: 'a[href="/edit"]', t: 'Дальше — редактирование', pre: function () { call('tab', 'res'); }, x: 'Если голова собрана, но нужно поправить место вручную — откройте «Редактирование».' }
  ];

  TOURS['/edit'] = [
    { t: 'Редактирование', x: 'Здесь правят модель вручную, как в Blender или ZBrush: <b>выделили место → выбрали действие → применили</b>. Вне выделения модель не меняется, любую правку можно отменить клавишей Z.' },
    { sel: '.view', t: 'Рабочий вид', x: 'Это модель. <kbd>ЛКМ</kbd> — действие инструмента (красить, рамка, двигать), <kbd>ПКМ</kbd> — вращать, <kbd>колесо</kbd> — масштаб, <kbd>СКМ</kbd> — сдвинуть. Подсказки внизу вида меняются вместе с инструментом.', pos: 'right' },
    { sel: '#t-brush', t: 'Инструменты слева', x: '<b>Кисть</b> (B) красит область, <b>Рамка</b> (X) обводит прямоугольник, <b>Двигать</b> (G) тянет выделенное, <b>Рисовать</b> (P) красит текстуру, <b>Вид</b> (R) вращает без выделения. Нажмите «Кисть».', wait: { sel: '#t-brush', ev: 'click' }, pos: 'right' },
    { sel: '.view', t: 'Попробуйте: выделите место', x: 'Проведите мышью по лицу, зажав левую кнопку. Выделенное место подсветится. Справа можно сменить размер кисти. Выделять не обязательно — «Далее» пропустит шаг.', cond: function () { return hasG('nsel') && G('nsel') > 0; }, pos: 'right' },
    { sel: '#info', t: 'Сколько выделено', x: 'Чип сверху показывает число выделенных вершин. Лишнее снимается режимом «Вычесть», кнопкой «Снять» или клавишей Esc.' },
    { sel: '.side .sec', t: '1. Область', x: '<b>Добавить / Вычесть</b> — режим кисти. <b>Размер кисти</b> меняется ползунком или клавишами <kbd>[</kbd> <kbd>]</kbd>. <b>Расширить / Сузить / Инвертировать</b> правят границу. <b>Симметрия по X</b> красит и зеркальное место. Область можно сохранить под именем. «Шаг назад» отменяет только выделение.' },
    { sel: '#opg', t: '2. Правка: что сделать', pre: function () { var s = $('#s-edit'); if (s) s.open = true; }, x: 'Выберите действие: <b>Сгладить</b>, <b>Сместить</b>, <b>Надуть</b>, <b>Выровнять</b>, <b>Сжать</b>, <b>Растянуть</b>. Ниже появляются только его параметры.' },
    { sel: '#ft', t: 'Мягкость края', x: 'Насколько плавно правка затухает к краю выделения. 0 — резкая граница, 1 — очень плавная. Двойной щелчок по любому ползунку возвращает значение по умолчанию.' },
    { sel: '#ba', t: 'Применить', x: 'Единственная главная кнопка. Серая, пока ничего не выделено — под ней написано почему. После применения тост скажет «Применено», <kbd>Z</kbd> вернёт как было.' },
    { sel: '#bsg', t: 'Посоветовать параметры', x: 'Помощник предлагает значения для сглаживания и объясняет почему. Он только предлагает — применяете вы.' },
    { sel: '#bu', t: 'Отмена и возврат', x: '<b>Отменить</b> (Z) и <b>Вернуть</b> (Shift+Z или Y) работают в текущем виде: выделение, правка сетки или мазок текстуры. «Показать «до»» сравнивает с состоянием до последней правки.' },
    { sel: '#vm', t: 'Сетка / Текстура / UV', x: 'Три вида одной модели. <b>Сетка</b> — форма. <b>Текстура</b> — модель с цветом, по ней можно рисовать. <b>UV</b> — плоская развёртка текстуры. «Текстура» и «UV» недоступны, если у модели нет развёртки — причина в подсказке кнопки.' },
    { sel: '#v-tex', t: 'Попробуйте: вид «Текстура»', x: 'Нажмите «Текстура» (если кнопка недоступна — у этой модели нет UV, пропустите).', wait: { sel: '#v-tex', ev: 'click' } },
    { sel: '#s-tex', t: '3. Текстура', pre: function () { if (!$('#v-tex').disabled) call('setView', 'tex'); var s = $('#s-tex'); if (s) s.open = true; }, x: 'Режимы кисти: <b>Краска</b>, <b>Стёрка</b> (возвращает оригинал), <b>Размыть</b>, <b>Светлее</b>, <b>Темнее</b>. Цвет, размер в пикселях и сила — ниже. Рисуйте мышью прямо по модели. «Сохранить» пишет в <code>work/head_edit.*</code>, оригинал не перезаписывается.' },
    { sel: '#vm', t: 'Вид «UV»', pre: function () { if (!$('#v-uv').disabled) call('setView', 'uv'); }, x: 'Плоская развёртка. Здесь же видно, как текстура лежит на модели. Выделенное место на модели подсвечено и на развёртке.' },
    { sel: '#s-uv', t: '4. UV (развёртка)', pre: function () { var s = $('#s-uv'); if (s && !s.hidden) s.open = true; }, x: 'Сдвиг, растяжение и поворот развёртки выделенного места. Сначала выделите место на модели (вид «Сетка» или «Текстура»), затем задайте число и нажмите кнопку.' },
    { sel: 'header.top button[title^="Загрузить"]', t: 'Файл: импорт и экспорт', pre: function () { call('setView', 'mesh'); }, x: 'Здесь загружают модель из файла проекта, с компьютера (.glb, .gltf, .obj) или из игры (.gm), и сохраняют результат в GLB, OBJ и PNG. Импорт ставит чужую часть на место стыка; отмена вернёт прежнюю.' },
    { sel: '#tree', pre: function () { var d = $('#dlg'); if (d && !d.open) d.showModal(); }, t: 'Дерево моделей', x: 'Как в Blender: группа → файл → часть. <b>Шаблон</b> — исходная голова. <b>Проект</b> — файлы из папок work и models. <b>Игра</b> — модели Корсаров. Раскройте файл — увидите его части (из чего он состоит) и число вершин; «мелкая» — слишком маленькая часть. Щёлкните нужную часть.' },
    { sel: '#picked', pre: function () { var d = $('#dlg'); if (d && !d.open) d.showModal(); }, t: 'Что выбрано', x: 'Здесь всегда написано: файл › часть, которая будет открыта. Пока ничего не выбрано — кнопка ничего не сделает.' },
    { sel: '#sc', pre: function () { var d = $('#dlg'); if (d && !d.open) d.showModal(); }, t: 'Как вставить', x: '<b>Показать как есть</b> — часть открывается целиком, без манекена (обычный выбор, чтобы посмотреть и править модель). <b>На шею манекена</b> — замена головы: часть подгоняется по кольцу шеи и сшивается. <b>Без масштаба</b> — то же, но размер не меняется. Подсказка под полем меняется с выбором.' },
    { sel: '#brp', pre: function () { var d = $('#dlg'); if (d && !d.open) d.showModal(); }, t: 'Открыть в редакторе', x: 'Запускает загрузку: полоса показывает ход и оставшееся время, «Отмена» останавливает без изменений. Результат — в окне; «Отменить» в шапке вернёт прежнюю сцену. Ошибка остаётся красным блоком с названием файла и части.' },
    { sel: '#s-log', pre: function () { var d = $('#dlg'); if (d && d.open) d.close(); }, t: 'Журнал правок', x: 'Список всех применённых правок по порядку. Открывается по клику.' },
    { t: 'Клавиши', x: '<kbd>B</kbd> кисть · <kbd>X</kbd> рамка · <kbd>G</kbd> двигать · <kbd>P</kbd> рисовать · <kbd>R</kbd> вид<br><kbd>Z</kbd> назад · <kbd>Shift+Z</kbd> / <kbd>Y</kbd> вперёд · <kbd>Esc</kbd> снять выделение<br><kbd>[</kbd> <kbd>]</kbd> размер кисти. Работают и в русской раскладке. Гайд готов — правьте.' }
  ];

  TOURS['/model'] = [
    { t: 'Модель: части и замена', x: 'Отдельный режим для любого GLB: посмотреть, из каких частей он состоит, заменить, добавить или убрать часть, пересобрать сетку. Исходный файл не меняется — результат пишется в новый.' },
    { sel: '#f', t: 'Файл', x: 'Выберите модель из папок <code>work</code> и <code>models</code>.' },
    { sel: '#pv', t: 'Превью модели', x: 'Модель в 3D. Левая кнопка — вращать, колесо — масштаб, правая — сдвиг. Щёлкните по части на модели или по строке таблицы: она подсветится, остальные станут прозрачными. Второе превью в шаге 2 показывает часть-источник.' },
    { sel: '#t', t: 'Части файла', x: 'Таблица: имя части, число вершин и треугольников, есть ли UV и текстура, габариты. По ней находят, что именно менять.' },
    { sel: '#n', t: 'Заменить / добавить / убрать', x: 'Выберите часть в этом файле, затем файл и часть-источник (на что заменять). Имя нового файла можно не писать. Кнопки: «заменить», «добавить из другого файла», «убрать».' },
    { sel: '#fc', t: 'Ремеш и UV', x: 'Задайте целевое число треугольников, длину ребра или число подразбиений и нажмите «ремеш». Новая UV и текстура переносятся автоматически. «Только новая UV» оставляет сетку.' },
    { sel: '#res', t: 'Результат', x: 'После операции здесь появится путь нового файла или «ошибка». Файл сразу попадает в список выше.' }
  ];

  TOURS['/review'] = [
    { t: 'Сравнение вариантов', x: 'Система показывает два варианта одной и той же проблемы (A и B), вы выбираете лучший. Ваши выборы учат оценщика, и со временем он решает сам.' },
    { sel: '#st', t: 'Статистика', x: 'Сколько пар ждёт, сколько вы выбрали, сколько решил оценщик и насколько он точен.' },
    { sel: '#foc', t: 'Область работы', x: 'Можно выделить мышью прямоугольник на картинке — тогда сравнивается только он (например, глаз). «Снять» возвращает всю картинку.' },
    { sel: '#cur', t: 'Текущая пара', x: 'Слева «до», затем A и B. Кнопки: «A лучше» (клавиша <kbd>A</kbd>), «B лучше» (<kbd>B</kbd>), «Одинаково», «Оба хуже», «Пропустить» (<kbd>S</kbd>). В заметке напишите, что не так. Если пар нет, окно просто ждёт.' },
    { sel: '#hist', t: 'История', x: 'Решённые пары: кто решил (вы или оценщик) и что выбрано.' }
  ];

  TOURS['/proto'] = [
    { t: 'Прототипы', x: 'Это макеты будущих экранов с выдуманными данными, не рабочий код. Их можно щёлкать, чтобы увидеть идею: выделение, сравнение A/B, ручная правка, замена части, обучение.' },
    { sel: '#nav', t: 'Вкладки', x: 'Каждая вкладка — отдельный прототип с пояснением «как это работает» наверху.' },
    { sel: '#p1 .how', t: 'Пояснение', x: 'Под заголовком каждого прототипа — шаги: что показано и что можно нажать. Рабочие версии — «Конвейер» и «Редактирование».' }
  ];

  /* ---------------- движок ---------------- */
  var path = location.pathname.replace(/\/+$/, '') || '/';
  var steps = [], idx = 0, mode = '', ui = null, timer = null, waitOff = null;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  function css() {
    var s = document.createElement('style');
    s.textContent =
      '#tour-btn{position:fixed;left:12px;bottom:40px;z-index:2147483000;min-height:36px;padding:0 14px;border-radius:18px;border:1px solid #1f3fbf;background:#2447d6;color:#fff;font:600 13px system-ui,sans-serif;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.35)}' +
      '#tour-btn.in-header{position:static;margin-left:8px;box-shadow:none}#tour-btn:focus-visible,.tour-b:focus-visible{outline:3px solid #ffb703;outline-offset:2px}' +
      '#tour-menu{position:fixed;right:12px;top:56px;z-index:2147483000;width:min(340px,calc(100vw - 24px));background:#fff;color:#16181d;border:1px solid #b8bcc6;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.4);padding:12px;font:14px/1.4 system-ui,sans-serif}' +
      '#tour-menu h4{margin:0 0 8px;font-size:14px}#tour-menu button{display:flex;width:100%;justify-content:space-between;gap:8px;min-height:36px;align-items:center;margin:2px 0;padding:0 10px;border:1px solid #c9ccd4;border-radius:8px;background:#f5f6f9;color:#16181d;font:13px system-ui,sans-serif;cursor:pointer;text-align:left}' +
      '#tour-menu button.cur{border-color:#2447d6;font-weight:650}#tour-menu button.all{background:#2447d6;color:#fff;border-color:#1f3fbf;font-weight:650;margin-bottom:8px}' +
      '#tour-hl{position:fixed;z-index:2147482990;border:2px solid #ffb703;border-radius:8px;box-shadow:0 0 0 9999px rgba(8,10,16,.62);pointer-events:none;transition:all .18s ease}' +
      '#tour-card{position:fixed;z-index:2147483001;width:min(380px,calc(100vw - 24px));background:#fff;color:#16181d;border-radius:12px;box-shadow:0 10px 36px rgba(0,0,0,.5);padding:16px;font:14px/1.5 system-ui,sans-serif}' +
      '#tour-card h3{margin:0 0 6px;font-size:16px}#tour-card p{margin:0 0 10px}#tour-card kbd{border:1px solid #aeb3bf;border-bottom-width:2px;border-radius:4px;padding:0 5px;font:12px monospace;background:#f1f2f6}' +
      '#tour-card code{background:#eef0f5;padding:0 4px;border-radius:4px}' +
      '#tour-card .meta{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#4a4f5c;margin-bottom:6px}' +
      '#tour-card .bar{height:4px;background:#e3e5ec;border-radius:2px;margin-bottom:10px;overflow:hidden}#tour-card .bar i{display:block;height:100%;background:#2447d6}' +
      '#tour-card .try{background:#fff6dc;border:1px solid #f0c75e;border-radius:8px;padding:6px 10px;margin:0 0 10px;font-size:13px}#tour-card .try.ok{background:#e4f6e8;border-color:#7cc58d}' +
      '#tour-card .row{display:flex;gap:8px;justify-content:space-between}.tour-b{min-height:36px;padding:0 14px;border:1px solid #b8bcc6;border-radius:8px;background:#f5f6f9;color:#16181d;font:600 13px system-ui,sans-serif;cursor:pointer}.tour-b.pri{background:#2447d6;border-color:#1f3fbf;color:#fff}.tour-b:disabled{opacity:.5;cursor:not-allowed}' +
      '#tour-toast{position:fixed;left:12px;bottom:84px;z-index:2147483000;width:min(320px,calc(100vw - 24px));background:#fff;color:#16181d;border:1px solid #2447d6;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.4);padding:12px;font:14px/1.4 system-ui,sans-serif}' +
      '@media (prefers-reduced-motion:reduce){#tour-hl{transition:none}}';
    document.head.appendChild(s);
  }

  function el(tag, id, html) { var e = document.createElement(tag); if (id) e.id = id; if (html != null) e.innerHTML = html; document.body.appendChild(e); return e; }
  function visible(e) { if (!e || e.hidden) return false; var r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2 && getComputedStyle(e).visibility !== 'hidden'; }

  function place() {
    if (!ui) return;
    var s = steps[idx], target = s.sel ? $(s.sel) : null, hl = ui.hl, card = ui.card, vw = innerWidth, vh = innerHeight, m = 12;
    if (target && !visible(target) && target.closest && target.closest('details:not([open])')) { target.closest('details').open = true; }
    if (target && visible(target)) {
      var r = target.getBoundingClientRect();
      if (r.bottom < 0 || r.top > vh) { target.scrollIntoView({ block: 'center' }); r = target.getBoundingClientRect(); }
      var big = r.width > vw * 0.6 && r.height > vh * 0.6;
      var x = Math.max(0, r.left - 4), y = Math.max(0, r.top - 4), w = Math.min(vw - x, r.width + 8), h = Math.min(vh - y, r.height + 8);
      hl.style.cssText = 'display:block;left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + h + 'px' + (big ? ';box-shadow:none' : '');
      var cw = card.offsetWidth, ch = card.offsetHeight, cx, cy;
      if (big || s.pos === 'right' && r.right + cw + m > vw) { cx = vw - cw - m; cy = vh - ch - 44; if (!big) { cy = Math.min(Math.max(m, r.top + 20), vh - ch - m); } }
      else if (s.pos === 'right') { cx = r.right + m; cy = Math.min(Math.max(m, r.top), vh - ch - m); }
      else if (r.bottom + ch + m < vh) { cx = r.left; cy = r.bottom + m; }
      else if (r.top - ch - m > 0) { cx = r.left; cy = r.top - ch - m; }
      else if (r.left - cw - m > 0) { cx = r.left - cw - m; cy = Math.min(Math.max(m, r.top), vh - ch - m); }
      else { cx = r.right + m; cy = Math.min(Math.max(m, r.top), vh - ch - m); }
      cx = Math.min(Math.max(m, cx), vw - cw - m); cy = Math.min(Math.max(m, cy), vh - ch - m);
      card.style.left = cx + 'px'; card.style.top = cy + 'px';
    } else {
      hl.style.cssText = 'display:block;left:50%;top:50%;width:0;height:0;border:0;box-shadow:0 0 0 9999px rgba(8,10,16,.62)';
      card.style.left = Math.max(m, (vw - card.offsetWidth) / 2) + 'px'; card.style.top = Math.max(m, (vh - card.offsetHeight) / 2.4) + 'px';
    }
  }

  function clearWait() { if (waitOff) { waitOff(); waitOff = null; } }

  function render() {
    var s = steps[idx], last = idx == steps.length - 1;
    clearWait();
    try { if (s.pre) s.pre(); } catch (e) {}
    var interactive = !!(s.wait || s.cond);
    ui.card.innerHTML =
      '<div class="meta"><span>' + pageName() + ' · шаг ' + (idx + 1) + ' из ' + steps.length + '</span><button class="tour-b" id="tour-x" aria-label="Закрыть гайд" style="min-height:28px;padding:0 8px">✕</button></div>' +
      '<div class="bar"><i style="width:' + Math.round((idx + 1) / steps.length * 100) + '%"></i></div>' +
      '<h3>' + s.t + '</h3><p>' + s.x + '</p>' +
      (interactive ? '<div class="try" id="tour-try">Попробуйте сами — после действия гайд пойдёт дальше. Можно нажать «Далее», чтобы пропустить.</div>' : '') +
      '<div class="row"><button class="tour-b" id="tour-p"' + (idx ? '' : ' disabled') + '>← Назад</button>' +
      '<button class="tour-b pri" id="tour-n">' + (last ? (nextPage() ? 'Дальше: ' + nextPage()[1] : 'Готово') : 'Далее →') + '</button></div>';
    ui.card.setAttribute('role', 'dialog'); ui.card.setAttribute('aria-live', 'polite'); ui.card.setAttribute('aria-label', 'Гайд: ' + s.t);
    $('#tour-x').onclick = stop; $('#tour-p').onclick = function () { go(idx - 1); }; $('#tour-n').onclick = function () { go(idx + 1); };
    place();
    try { $('#tour-n').focus({ preventScroll: true }); } catch (e) {}
    setTimeout(place, 120);
    if (s.wait) {
      var t = $(s.wait.sel), done = function () { ok(); };
      if (t) { t.addEventListener(s.wait.ev, done, { once: true }); waitOff = function () { t.removeEventListener(s.wait.ev, done); }; }
    }
  }
  function ok() { var t = $('#tour-try'); if (t) { t.className = 'try ok'; t.textContent = 'Получилось! Переходим дальше…'; } var i = idx; setTimeout(function () { if (ui && idx === i) go(i + 1); }, 700); }

  function pageName() { for (var i = 0; i < PAGES.length; i++) if (PAGES[i][0] === path) return PAGES[i][1].split(':')[0]; return 'Гайд'; }
  function nextPage() { if (mode !== 'all') return null; for (var i = 0; i < PAGES.length; i++) if (PAGES[i][0] === path) return PAGES[i + 1] || null; return null; }

  function go(i) {
    if (i < 0) return;
    if (i >= steps.length) { finish(); return; }
    idx = i; render();
  }
  function finish() {
    store.set('tour_done_' + path, '1');
    var np = nextPage(), m = mode;
    stop();
    if (np) location.href = np[0] + '?tour=all';
  }
  function stop() {
    clearWait(); if (timer) { clearInterval(timer); timer = null; }
    if (ui) { ui.hl.remove(); ui.card.remove(); ui = null; }
    document.removeEventListener('keydown', onKey, true);
    removeEventListener('resize', place);
  }
  function onKey(e) {
    if (!ui) return;
    var k = e.key;
    if (k === 'Escape') { e.stopImmediatePropagation(); e.preventDefault(); stop(); }
    else if ((k === 'ArrowRight' || k === 'Enter') && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) && e.target.id !== 'tour-p') { e.stopImmediatePropagation(); e.preventDefault(); go(idx + 1); }
    else if (k === 'ArrowLeft' && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) { e.stopImmediatePropagation(); e.preventDefault(); go(idx - 1); }
  }

  function start(m, from) {
    closeMenu(); var t = $('#tour-toast'); if (t) t.remove();
    steps = TOURS[path]; if (!steps) return;
    if (ui) stop();
    mode = m || '1'; idx = from || 0;
    ui = { hl: el('div', 'tour-hl'), card: el('div', 'tour-card') };
    document.addEventListener('keydown', onKey, true); addEventListener('resize', place);
    timer = setInterval(function () {
      place();
      var s = steps[idx];
      if (s && s.cond) { try { if (s.cond()) { s.cond = null; ok(); } } catch (e) {} }
    }, 350);
    render();
  }

  function closeMenu() { var m = $('#tour-menu'); if (m) m.remove(); }
  function openMenu() {
    if ($('#tour-menu')) { closeMenu(); return; }
    var h = '<h4>Интерактивный гайд</h4>' +
      '<button class="all" id="tm-all">Пройти все окна подряд <span>6 окон</span></button>';
    PAGES.forEach(function (p, i) {
      var done = store.get('tour_done_' + p[0]) ? '✓' : '';
      h += '<button data-i="' + i + '"' + (p[0] === path ? ' class="cur"' : '') + '><span>' + p[1] + '</span><span>' + (p[0] === path ? 'здесь ' : '') + done + '</span></button>';
    });
    var m = el('div', 'tour-menu', h); m.setAttribute('role', 'dialog'); m.setAttribute('aria-label', 'Меню гайда'); if (!document.querySelector('header')) m.style.cssText = 'left:12px;bottom:84px;right:auto;top:auto';
    m.onclick = function (e) {
      var b = e.target.closest('button'); if (!b) return;
      if (b.id === 'tm-all') { if (path === '/') start('all'); else location.href = '/?tour=all'; return; }
      var p = PAGES[+b.dataset.i];
      if (p[0] === path) start('1'); else location.href = p[0] + '?tour=1';
    };
  }

  function init() {
    if (!TOURS[path]) return;
    css();
    var b = el('button', 'tour-btn', '? Гайд'); b.setAttribute('aria-label', 'Интерактивный гайд: как пользоваться'); b.title = 'Пошаговый гайд по этому окну и по всем окнам';
    b.onclick = openMenu;
    var hd = document.querySelector('header'); if (hd) { b.className = 'in-header'; hd.appendChild(b); }
    var q = location.search.match(/[?&]tour=(\w+)/);
    if (q) { setTimeout(function () { start(q[1]); }, 900); try { history.replaceState(null, '', location.pathname); } catch (e) {} return; }
    if (!store.get('tour_seen')) {
      store.set('tour_seen', '1');
      var t = el('div', 'tour-toast', '<b>Первый раз здесь?</b><br>Пройдите гайд — это минута, и всё станет понятно.<div style="display:flex;gap:8px;margin-top:10px"><button class="tour-b pri" id="tt-go">Пройти гайд</button><button class="tour-b" id="tt-no">Не сейчас</button></div>');
      $('#tt-go').onclick = function () { start('1'); };
      $('#tt-no').onclick = function () { t.remove(); };
    }
  }
  window.HWTour = { start: start, steps: TOURS, pages: PAGES };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
