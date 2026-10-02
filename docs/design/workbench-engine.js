/* Synthetic workbench model and a deliberately small formula language. No network, eval or dependencies.
   This browser prototype demonstrates transitions; it is not authorization or a concurrent lock service. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.WorkbenchEngine = api;
})(typeof window !== 'undefined' ? window : typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const statuses = Object.freeze(['План', 'Заказано', 'В пути', 'Получено']);
  const suppliers = Object.freeze(['Демо · Мастерская Север', 'Демо · Текстильная линия', 'Демо · Форма и ткань']);
  const editable = ['productId', 'qty', 'price', 'date', 'supplier', 'status'];
  const actors = { owner: 'Руководитель', manager: 'Сотрудник' };
  const copy = value => JSON.parse(JSON.stringify(value));
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const present = value => value !== null && value !== undefined;

  function createState(catalog) {
    const products = Array.isArray(catalog) ? catalog.filter(product => product && typeof product.id === 'string') : [];
    const rows = products.length ? Array.from({ length: 12 }, (_, index) => {
      const product = products[(index * 3 + 1) % products.length];
      return {
        id: 'purchase-' + String(index + 1).padStart(3, '0'),
        productId: product.id,
        qty: [80, 120, 40, 60, 100, 30, 90, 50, 160, 70, 35, 110][index],
        price: typeof product.cost === 'number' && Number.isFinite(product.cost) ? product.cost : 450 + index * 75,
        date: '2026-10-' + String(3 + index * 2).padStart(2, '0'),
        supplier: suppliers[index % suppliers.length],
        status: statuses[Math.floor(index / 3)],
      };
    }) : [];
    return { schema: 1, revision: 7, rows: rows, drafts: {}, lock: null, request: null, history: [] };
  }

  function rowsFor(state, profile) {
    const draft = state.drafts && state.drafts[profile];
    return copy(state.lock && state.lock.owner === profile && draft ? draft.rows : state.rows);
  }

  function diffRows(base, proposed) {
    const before = new Map(base.map(row => [row.id, row]));
    const after = new Map(proposed.map(row => [row.id, row]));
    const changes = [];
    proposed.forEach(row => {
      const previous = before.get(row.id);
      if (!previous) {
        changes.push({ rowId: row.id, field: '*', before: null, after: copy(row), kind: 'add' });
        return;
      }
      editable.forEach(field => {
        if (previous[field] !== row[field]) changes.push({ rowId: row.id, field: field, before: previous[field], after: row[field], kind: 'edit' });
      });
    });
    base.forEach(row => {
      if (!after.has(row.id)) changes.push({ rowId: row.id, field: '*', before: copy(row), after: null, kind: 'delete' });
    });
    return changes;
  }

  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const [year, month, day] = value.split('-').map(Number);
    if (year < 1900 || year > 2200 || month < 1 || month > 12 || day < 1) return false;
    return day <= new Date(Date.UTC(year, month, 0)).getUTCDate();
  }

  function typedValue(field, value, catalog) {
    if (field === 'qty' || field === 'price') {
      if (typeof value === 'string' && /^\s*\d+(?:[.,]\d+)?\s*$/.test(value)) value = Number(value.trim().replace(',', '.'));
      if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1e12) throw new Error(field === 'qty' ? 'Количество: введите число от 0 до 1 000 000 000 000.' : 'Цена: введите число от 0 до 1 000 000 000 000.');
      return value;
    }
    if (field === 'date') {
      if (!validDate(value)) throw new Error('Укажите существующую дату в формате ГГГГ-ММ-ДД.');
      return value;
    }
    if (field === 'supplier') {
      if (!suppliers.includes(value)) throw new Error('Выберите поставщика из справочника.');
      return value;
    }
    if (field === 'status') {
      if (!statuses.includes(value)) throw new Error('Выберите допустимый статус.');
      return value;
    }
    if (field === 'productId') {
      if (typeof value !== 'string' || !catalog.some(product => product.id === value)) throw new Error('Товар не найден в связанном каталоге.');
      return value;
    }
    throw new Error('Это поле защищено от редактирования.');
  }

  function validRows(rows, catalog) {
    const seen = new Set();
    if (!Array.isArray(rows) || rows.length > 1000) throw new Error('В демо поддерживается до 1 000 строк.');
    rows.forEach(row => {
      if (!row || typeof row.id !== 'string' || !row.id || seen.has(row.id)) throw new Error('Некорректный или повторяющийся ID строки.');
      if (Object.keys(row).some(key => key !== 'id' && !editable.includes(key))) throw new Error('В строке есть неподдерживаемое поле.');
      seen.add(row.id);
      editable.forEach(field => { row[field] = typedValue(field, row[field], catalog); });
    });
  }

  function actionTime(action, state) {
    if (typeof action.at === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(action.at) && Number.isFinite(Date.parse(action.at))) return action.at;
    // A stable scenario clock keeps transition deterministic. The UI may supply action.at.
    return new Date(Date.UTC(2026, 9, 2, 6, 0, (state.history || []).length)).toISOString();
  }

  function transition(state, action, catalog) {
    const fail = message => ({ state: state, error: message, message: message });
    if (!state || state.schema !== 1 || !Array.isArray(state.rows) || !state.drafts || !Array.isArray(state.history)) return fail('Состояние демо повреждено. Сбросьте демо.');
    if (!action || !own(actors, action.profile)) return fail('Неизвестный демонстрационный профиль.');
    const profile = action.profile;
    const products = Array.isArray(catalog) ? catalog : [];
    const next = copy(state);
    const at = actionTime(action, state);
    let message = '';
    const requireLock = () => {
      if (next.request) throw new Error('Таблица ожидает решения по согласованию.');
      if (!next.lock || next.lock.owner !== profile) throw new Error('Сначала возьмите таблицу в работу.');
      const draft = next.drafts[profile];
      if (!draft || draft.baseRevision !== next.revision) throw new Error('Черновик основан на старой версии. Сравните изменения и создайте новый черновик.');
      return draft;
    };
    const requireApprover = () => {
      if (profile !== 'owner') throw new Error('В демонстрации согласование доступно руководителю.');
      if (!next.request) throw new Error('Нет заявки на согласование.');
      return next.request;
    };
    try {
      switch (action.type) {
        case 'acquire': {
          if (next.request) throw new Error('Сначала необходимо завершить согласование.');
          if (next.lock && next.lock.owner !== profile) throw new Error('Таблица уже в работе у другого сотрудника.');
          if (next.drafts[profile] && next.drafts[profile].baseRevision !== next.revision) throw new Error('Сохранённый черновик устарел. Сравните изменения или удалите свой черновик перед новой работой.');
          if (next.lock && next.lock.owner === profile) return { state: state, error: null, message: 'Таблица уже у вас в работе.' };
          next.drafts[profile] = next.drafts[profile] || { baseRevision: next.revision, rows: copy(next.rows), createdAt: at, updatedAt: at };
          next.lock = { owner: profile, at: at };
          message = 'Таблица взята в работу. Изменения сохраняются в личном черновике.';
          break;
        }
        case 'release': {
          const draft = requireLock();
          draft.updatedAt = at;
          next.lock = null;
          message = 'Таблица освобождена. Ваш черновик сохранён.';
          break;
        }
        case 'discard': {
          if (next.request && next.request.author === profile) throw new Error('Отправленный черновик сначала нужно вернуть с согласования.');
          if (!next.drafts[profile]) throw new Error('У вас нет черновика.');
          delete next.drafts[profile];
          if (next.lock && next.lock.owner === profile) next.lock = null;
          message = 'Ваш черновик удалён. Утверждённые данные сохранены.';
          break;
        }
        case 'edit': {
          const draft = requireLock();
          if (!Array.isArray(action.patches) || action.patches.length === 0 || action.patches.length > 2000) throw new Error('Выберите от 1 до 2 000 ячеек для изменения.');
          action.patches.forEach(patch => {
            if (!patch || !editable.includes(patch.field)) throw new Error('Вставка затрагивает защищённое или неизвестное поле.');
            const row = draft.rows.find(item => item.id === patch.rowId);
            if (!row) throw new Error('Строка не найдена.');
            row[patch.field] = typedValue(patch.field, patch.value, products);
          });
          validRows(draft.rows, products);
          draft.updatedAt = at;
          message = 'Изменения ячеек сохранены в черновике (' + action.patches.length + ').';
          break;
        }
        case 'add': {
          const draft = requireLock();
          if (!action.row || typeof action.row !== 'object' || Array.isArray(action.row)) throw new Error('Заполните поля новой записи.');
          const row = copy(action.row);
          if (!present(row.id)) row.id = 'purchase-new-' + next.revision + '-' + (next.history.length + 1);
          draft.rows.push(row);
          validRows(draft.rows, products);
          draft.updatedAt = at;
          message = 'Новая запись добавлена в черновик.';
          break;
        }
        case 'submit': {
          const draft = requireLock();
          validRows(draft.rows, products);
          if (!diffRows(next.rows, draft.rows).length) throw new Error('В черновике пока нет изменений для согласования.');
          const comment = typeof action.comment === 'string' ? action.comment.trim().slice(0, 2000) : '';
          next.request = { id: 'request-' + next.revision + '-' + (next.history.length + 1), author: profile, baseRevision: next.revision, rows: copy(draft.rows), comment: comment, at: at };
          next.lock = null;
          message = 'Черновик отправлен на согласование. Общие значения пока не изменились.';
          break;
        }
        case 'approve': {
          const request = requireApprover();
          if (request.baseRevision !== next.revision) throw new Error('Общие данные уже изменились. Заявку нужно вернуть и сверить с новой версией.');
          validRows(request.rows, products);
          next.rows = copy(request.rows);
          next.revision += 1;
          delete next.drafts[request.author];
          next.request = null;
          next.lock = null;
          message = 'Изменения согласованы и применены. Общая версия: ' + next.revision + '.';
          break;
        }
        case 'return': {
          const request = requireApprover();
          const comment = typeof action.comment === 'string' ? action.comment.trim().slice(0, 2000) : '';
          if (!comment) throw new Error('Укажите, что нужно исправить в черновике.');
          const previous = next.drafts[request.author];
          next.drafts[request.author] = { baseRevision: request.baseRevision, rows: copy(request.rows), createdAt: previous ? previous.createdAt : request.at, updatedAt: at, reviewComment: comment };
          next.request = null;
          next.lock = null;
          message = 'Черновик возвращён автору с комментарием.';
          break;
        }
        default: throw new Error('Неизвестное действие.');
      }
      next.history.push({ id: 'event-' + (next.history.length + 1), type: action.type, profile: profile, actor: actors[profile], at: at, description: message });
      return { state: next, error: null, message: message };
    } catch (error) {
      return fail(error.message || 'Не удалось выполнить действие.');
    }
  }

  const functions = { SUM: 'SUM', 'СУММ': 'SUM', IF: 'IF', 'ЕСЛИ': 'IF', MIN: 'MIN', 'МИН': 'MIN', MAX: 'MAX', 'МАКС': 'MAX', ROUND: 'ROUND', 'ОКРУГЛ': 'ROUND' };
  const scalar = value => {
    if (value === null || value === undefined || value === '') return '';
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) throw new Error('Неконечное числовое значение.');
      return value;
    }
    if (typeof value === 'boolean') return value ? 1 : 0;
    if (typeof value !== 'string') throw new Error('Неподдерживаемое значение ячейки.');
    const trimmed = value.trim();
    if (/^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) {
      const number = Number(trimmed.replace(',', '.'));
      if (!Number.isFinite(number)) throw new Error('Слишком большое число.');
      return number;
    }
    return value;
  };
  const numeric = value => {
    if (value === '') return 0;
    const result = scalar(value);
    if (typeof result !== 'number') throw new Error('Для вычисления нужно число.');
    return result;
  };
  const finiteResult = value => {
    if (!Number.isFinite(value)) throw new Error('Результат слишком велик.');
    return value;
  };

  function tokenize(source) {
    const tokens = [];
    let offset = 0;
    while (offset < source.length) {
      const tail = source.slice(offset);
      if (/^\s/.test(tail)) { offset += 1; continue; }
      if (tail[0] === '"') {
        let text = '';
        let closed = false;
        offset += 1;
        while (offset < source.length) {
          if (source[offset] === '"') {
            if (source[offset + 1] === '"') { text += '"'; offset += 2; continue; }
            offset += 1; closed = true; break;
          }
          text += source[offset++];
        }
        if (!closed) throw new Error('Закройте кавычки строки.');
        tokens.push({ type: 'literal', value: text });
        continue;
      }
      if (tail[0] === '[') {
        const end = tail.indexOf(']');
        if (end < 0) throw new Error('Закройте ссылку на поле символом ].');
        const name = tail.slice(1, end).trim();
        if (!name || name.length > 80) throw new Error('Некорректное имя поля.');
        tokens.push({ type: 'field', value: name });
        offset += end + 1;
        continue;
      }
      const number = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(tail);
      if (number) { tokens.push({ type: 'literal', value: Number(number[0]) }); offset += number[0].length; continue; }
      const identifier = /^[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_0-9]*/.exec(tail);
      if (identifier) {
        const value = identifier[0].toUpperCase();
        tokens.push({ type: /^[A-Z]{1,3}[1-9]\d{0,4}$/.test(value) ? 'cell' : 'name', value: value });
        offset += identifier[0].length;
        continue;
      }
      const operator = /^(>=|<=|<>|!=|==|[+\-*/()=<>;,:])/.exec(tail);
      if (operator) { tokens.push({ type: 'symbol', value: operator[0] }); offset += operator[0].length; continue; }
      throw new Error('Недопустимый символ в формуле: ' + tail[0]);
    }
    tokens.push({ type: 'end', value: '' });
    return tokens;
  }

  function parse(source) {
    const tokens = tokenize(source);
    let position = 0;
    let depth = 0;
    const peek = () => tokens[position];
    const consume = value => peek().value === value ? (++position, true) : false;
    const expect = value => { if (!consume(value)) throw new Error('Ожидается «' + value + '».'); };
    function expression() {
      if (++depth > 40) throw new Error('Слишком много вложенных выражений.');
      let left = sum();
      while (['=', '==', '!=', '<>', '<', '>', '<=', '>='].includes(peek().value)) {
        const op = tokens[position++].value;
        left = { type: 'binary', op: op, left: left, right: sum() };
      }
      depth -= 1;
      return left;
    }
    function sum() {
      let left = product();
      while (['+', '-'].includes(peek().value)) {
        const op = tokens[position++].value;
        left = { type: 'binary', op: op, left: left, right: product() };
      }
      return left;
    }
    function product() {
      let left = unary();
      while (['*', '/'].includes(peek().value)) {
        const op = tokens[position++].value;
        left = { type: 'binary', op: op, left: left, right: unary() };
      }
      return left;
    }
    function unary() {
      if (['+', '-'].includes(peek().value)) {
        if (++depth > 40) throw new Error('Слишком много вложенных выражений.');
        const op = tokens[position++].value;
        const node = { type: 'unary', op: op, argument: unary() };
        depth -= 1;
        return node;
      }
      return primary();
    }
    function primary() {
      if (consume('(')) { const node = expression(); expect(')'); return node; }
      const token = tokens[position++];
      if (!token || token.type === 'end') throw new Error('Формула не завершена.');
      if (token.type === 'literal' || token.type === 'field') return token;
      if (token.type === 'cell') {
        if (consume(':')) {
          const end = tokens[position++];
          if (!end || end.type !== 'cell') throw new Error('Укажите конец диапазона, например A1:B4.');
          return { type: 'range', start: token.value, end: end.value };
        }
        return token;
      }
      if (token.type === 'name') {
        if (token.value === 'TRUE' || token.value === 'ИСТИНА') return { type: 'literal', value: 1 };
        if (token.value === 'FALSE' || token.value === 'ЛОЖЬ') return { type: 'literal', value: 0 };
        if (!own(functions, token.value)) throw new Error('Неизвестная функция: ' + token.value);
        expect('(');
        const args = [];
        if (!consume(')')) {
          do { args.push(expression()); } while (consume(';') || consume(','));
          expect(')');
        }
        return { type: 'call', name: functions[token.value], args: args };
      }
      throw new Error('Неожиданный элемент формулы.');
    }
    const ast = expression();
    if (peek().type !== 'end') throw new Error('Проверьте операторы и разделители аргументов.');
    return ast;
  }

  function coordinates(address) {
    const match = /^([A-Z]+)(\d+)$/.exec(address);
    let column = 0;
    for (const letter of match[1]) column = column * 26 + letter.charCodeAt(0) - 64;
    return { column: column, row: Number(match[2]) };
  }

  function address(column, row) {
    let letters = '';
    while (column > 0) { column -= 1; letters = String.fromCharCode(65 + column % 26) + letters; column = Math.floor(column / 26); }
    return letters + row;
  }

  function evaluate(input, context) {
    const sourceContext = context || {};
    const cells = sourceContext.cells || {};
    const fields = sourceContext.fields || {};
    const visiting = new Set();
    const cache = new Map();
    let budget = 6000;
    function evaluateInput(value, depth) {
      if (depth > 40) throw new Error('Слишком длинная цепочка ссылок.');
      if (typeof value !== 'string' || value.trim()[0] !== '=') return scalar(value);
      const source = value.trim().slice(1);
      if (!source || source.length > 300) throw new Error('Формула должна содержать от 1 до 300 символов.');
      return visit(parse(source), depth + 1);
    }
    function resolveCell(reference, depth) {
      if (cache.has(reference)) return cache.get(reference);
      if (visiting.has(reference)) throw new Error('Циклическая ссылка: ' + reference + '.');
      visiting.add(reference);
      const value = own(cells, reference) ? evaluateInput(cells[reference], depth + 1) : 0;
      visiting.delete(reference);
      cache.set(reference, value === '' ? 0 : value);
      return value === '' ? 0 : value;
    }
    function visit(node, depth) {
      if (--budget < 0 || depth > 100) throw new Error('Превышен предел сложности вычисления.');
      switch (node.type) {
        case 'literal': return typeof node.value === 'number' ? finiteResult(node.value) : node.value;
        case 'field': {
          if (!own(fields, node.value)) throw new Error('Поле не найдено: ' + node.value + '.');
          return scalar(fields[node.value]);
        }
        case 'cell': return resolveCell(node.value, depth);
        case 'range': {
          const start = coordinates(node.start);
          const end = coordinates(node.end);
          const minColumn = Math.min(start.column, end.column);
          const maxColumn = Math.max(start.column, end.column);
          const minRow = Math.min(start.row, end.row);
          const maxRow = Math.max(start.row, end.row);
          if ((maxColumn - minColumn + 1) * (maxRow - minRow + 1) > 1000) throw new Error('Диапазон ограничен 1 000 ячейками.');
          const values = [];
          for (let row = minRow; row <= maxRow; row++) {
            for (let column = minColumn; column <= maxColumn; column++) values.push(resolveCell(address(column, row), depth));
          }
          return values;
        }
        case 'unary': return finiteResult((node.op === '-' ? -1 : 1) * numeric(visit(node.argument, depth + 1)));
        case 'binary': {
          const a = visit(node.left, depth + 1);
          const b = visit(node.right, depth + 1);
          if (Array.isArray(a) || Array.isArray(b)) throw new Error('Диапазон можно использовать внутри SUM, MIN или MAX.');
          if (node.op === '=') return a === b ? 1 : 0;
          if (node.op === '==') return a === b ? 1 : 0;
          if (node.op === '!=' || node.op === '<>') return a !== b ? 1 : 0;
          if (['>', '>=', '<', '<='].includes(node.op)) {
            const left = typeof a === 'string' && typeof b === 'string' ? a : numeric(a);
            const right = typeof a === 'string' && typeof b === 'string' ? b : numeric(b);
            return (node.op === '>' ? left > right : node.op === '>=' ? left >= right : node.op === '<' ? left < right : left <= right) ? 1 : 0;
          }
          const left = numeric(a);
          const right = numeric(b);
          if (node.op === '/' && right === 0) throw new Error('Деление на ноль.');
          return finiteResult(node.op === '+' ? left + right : node.op === '-' ? left - right : node.op === '*' ? left * right : left / right);
        }
        case 'call': {
          if (node.name === 'IF') {
            if (node.args.length !== 3) throw new Error('IF / ЕСЛИ принимает три аргумента.');
            const condition = visit(node.args[0], depth + 1);
            if (Array.isArray(condition)) throw new Error('Условие должно быть одним значением.');
            return visit(node.args[condition ? 1 : 2], depth + 1);
          }
          if (node.name === 'ROUND') {
            if (node.args.length < 1 || node.args.length > 2) throw new Error('ROUND / ОКРУГЛ принимает число и точность.');
            const value = numeric(visit(node.args[0], depth + 1));
            const precision = node.args.length > 1 ? numeric(visit(node.args[1], depth + 1)) : 0;
            if (!Number.isInteger(precision) || Math.abs(precision) > 10) throw new Error('Точность округления: целое число от −10 до 10.');
            const factor = Math.pow(10, precision);
            return finiteResult(Math.sign(value) * Math.round((Math.abs(value) + Number.EPSILON) * factor) / factor);
          }
          if (!node.args.length) throw new Error('Функции нужен хотя бы один аргумент.');
          const values = [];
          node.args.forEach(argument => {
            const value = visit(argument, depth + 1);
            if (Array.isArray(value)) value.forEach(item => { if (typeof item === 'number') values.push(item); });
            else values.push(numeric(value));
          });
          if (node.name === 'SUM') return finiteResult(values.reduce((sum, value) => finiteResult(sum + value), 0));
          if (!values.length) return 0;
          return node.name === 'MIN' ? Math.min.apply(null, values) : Math.max.apply(null, values);
        }
        default: throw new Error('Неизвестное выражение.');
      }
    }
    try {
      const value = evaluateInput(input, 0);
      if (Array.isArray(value)) throw new Error('Для диапазона используйте SUM, MIN или MAX.');
      if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Результат слишком велик.');
      return { value: value, error: null };
    } catch (error) {
      return { value: '', error: error.message || 'Ошибка формулы.' };
    }
  }

  return { createState: createState, transition: transition, rowsFor: rowsFor, diffRows: diffRows, evaluate: evaluate, statuses: statuses, suppliers: suppliers };
});
