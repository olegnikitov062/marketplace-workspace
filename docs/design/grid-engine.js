/* Local, synthetic prototype data and pure table operations. No network or dependencies. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.GridEngine = api;
})(typeof window !== 'undefined' ? window : typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const fields = [
    { id: 'id', label: 'ID', type: 'text', description: 'Уникальный идентификатор варианта в демо.' },
    { id: 'name', label: 'Товар', type: 'text' },
    { id: 'article', label: 'Артикул', type: 'text' },
    { id: 'brand', label: 'Бренд', type: 'enum', options: ['Линия', 'Тихо', 'Форма'] },
    { id: 'category', label: 'Категория', type: 'enum', options: ['Одежда', 'Сумки', 'Текстиль', 'Хранение'] },
    { id: 'cabinet', label: 'Кабинет', type: 'enum', options: ['WB · Основной', 'WB · Север'] },
    { id: 'owner', label: 'Ответственный', type: 'enum', options: ['Анна', 'Михаил', 'Олег'], editable: true },
    { id: 'status', label: 'Статус', type: 'enum', options: ['В продаже', 'Нет остатка', 'На паузе'] },
    { id: 'orders', label: 'Заказы', type: 'number', unit: 'шт', description: 'Заказы за последние 30 дней.' },
    { id: 'sales', label: 'Продажи', type: 'number', unit: 'шт', description: 'Проданные единицы за последние 30 дней.' },
    { id: 'returns', label: 'Возвраты', type: 'number', unit: 'шт' },
    { id: 'revenue', label: 'Выручка', type: 'number', unit: '₽', description: 'Демо: продажи × цена. Без учёта комиссий и возвратов.' },
    { id: 'stock', label: 'Остаток', type: 'number', unit: 'шт' },
    { id: 'coverage', label: 'Запас на', type: 'number', unit: 'дн', description: 'Остаток / средние продажи в день за 30 дней. Нет продаж — нет оценки.' },
    { id: 'plan', label: 'План продаж', type: 'number', unit: 'шт', editable: true },
    { id: 'cost', label: 'Себестоимость', type: 'number', unit: '₽', financial: true, editable: true, description: 'Себестоимость единицы. Пустое значение означает, что она неизвестна.' },
    { id: 'profit', label: 'Валовая прибыль', type: 'number', unit: '₽', financial: true, description: 'Демо: выручка − продажи × себестоимость. Комиссии и расходы ещё не включены.' },
    { id: 'margin', label: 'Валовая маржа', type: 'percent', unit: '%', financial: true, description: 'Валовая прибыль / выручка × 100. В итогах пересчитывается по известным данным.' },
    { id: 'note', label: 'Заметка', type: 'text', editable: true },
    { id: 'tag', label: 'Метка', type: 'enum', options: ['Новинка', 'Проверить', 'Приоритет', ''], editable: true },
  ];

  const products = [
    ['Футболка базовая · молочный / S', 'Одежда', 1290],
    ['Футболка базовая · графит / M', 'Одежда', 1290],
    ['Лонгслив свободный · белый / M', 'Одежда', 1890],
    ['Худи без принта · серый / L', 'Одежда', 3290],
    ['Брюки прямые · чёрный / M', 'Одежда', 2990],
    ['Рубашка льняная · песочный / L', 'Одежда', 2790],
    ['Шоппер большой · натуральный', 'Сумки', 990],
    ['Сумка через плечо · чёрный', 'Сумки', 2190],
    ['Косметичка стёганая · оливковый', 'Сумки', 890],
    ['Рюкзак городской · графит', 'Сумки', 3490],
    ['Сумка поясная · бежевый', 'Сумки', 1490],
    ['Чехол для ноутбука · серый / 14″', 'Сумки', 1690],
    ['Полотенце вафельное · белый', 'Текстиль', 590],
    ['Плед хлопковый · песочный', 'Текстиль', 2590],
    ['Наволочка декоративная · олива', 'Текстиль', 790],
    ['Салфетки столовые · набор 4 шт', 'Текстиль', 1190],
    ['Дорожка на стол · натуральный', 'Текстиль', 1390],
    ['Полотенце банное · серый', 'Текстиль', 1490],
    ['Корзина тканевая · малая', 'Хранение', 790],
    ['Органайзер для белья · 6 ячеек', 'Хранение', 690],
    ['Кофр под кровать · серый', 'Хранение', 1590],
    ['Короб для хранения · 30 л', 'Хранение', 1290],
    ['Мешок для стирки · набор 3 шт', 'Хранение', 490],
    ['Органайзер подвесной · бежевый', 'Хранение', 990],
    ['Футболка базовая · молочный / M', 'Одежда', 1290],
    ['Футболка базовая · молочный / L', 'Одежда', 1290],
    ['Худи без принта · оливковый / M', 'Одежда', 3290],
    ['Лонгслив свободный · графит / L', 'Одежда', 1890],
    ['Шоппер большой · чёрный', 'Сумки', 990],
    ['Сумка через плечо · бежевый', 'Сумки', 2190],
    ['Плед хлопковый · графит', 'Текстиль', 2590],
    ['Наволочка декоративная · песок', 'Текстиль', 790],
    ['Полотенце банное · белый', 'Текстиль', 1490],
    ['Корзина тканевая · большая', 'Хранение', 1190],
    ['Короб для хранения · 45 л', 'Хранение', 1590],
    ['Органайзер для белья · 12 ячеек', 'Хранение', 890],
  ];
  const salesByIndex = [124, 76, 42, 38, 23, 17, 186, 68, 92, 19, 58, 31, 208, 27, 83, 46, 12, 69, 137, 173, 24, 55, 0, 44, 112, 87, 0, 36, 155, 48, 14, 63, 75, 91, 34, 0];
  const stockByIndex = [84, 19, 61, 0, 92, 45, 412, 21, 138, 78, 11, 47, 0, 89, 33, 96, 64, 102, 266, 28, 111, 67, 180, 85, 34, 16, 0, 27, 380, 58, 72, 115, 12, 143, 59, 240];
  const rows = products.map(function (product, i) {
    const sales = salesByIndex[i];
    const cost = [3, 16, 28, 35].includes(i) ? null : Math.round(product[2] * (0.39 + (i % 5) * 0.08));
    const revenue = sales * product[2];
    const profit = cost === null ? null : revenue - sales * cost;
    return {
      id: 'demo-' + String(i + 1).padStart(3, '0'),
      name: product[0], article: 'DEMO-' + String(1001 + i),
      brand: ['Линия', 'Тихо', 'Форма'][i % 3], category: product[1],
      cabinet: i % 3 === 1 ? 'WB · Север' : 'WB · Основной',
      owner: ['Анна', 'Михаил', 'Олег'][(i + Math.floor(i / 6)) % 3],
      status: stockByIndex[i] === 0 ? 'Нет остатка' : i === 22 || i === 35 ? 'На паузе' : 'В продаже',
      orders: sales ? sales + Math.round(sales * (0.08 + (i % 4) * 0.04)) : 0,
      sales: sales, returns: Math.min(sales, Math.floor(sales * (i % 4) / 40)),
      revenue: revenue, stock: stockByIndex[i],
      coverage: sales > 0 ? Math.round(stockByIndex[i] / sales * 300) / 10 : null,
      plan: i === 26 ? 0 : Math.ceil(Math.max(sales, 20) * 1.2 / 10) * 10,
      cost: cost, profit: profit, margin: revenue > 0 && profit !== null ? profit / revenue * 100 : null,
      note: i === 3 ? 'Уточнить себестоимость' : i === 12 ? 'Ожидается поставка' : i === 26 ? 'Сезонный товар' : i % 7 === 0 ? 'Проверить карточку' : i % 2 ? '' : null,
      tag: i % 11 === 0 ? 'Новинка' : i % 7 === 0 ? 'Проверить' : i % 5 === 0 ? 'Приоритет' : '',
    };
  });

  const collator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' });
  const ops = ['contains', 'notContains', 'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'between', 'empty', 'notEmpty'];
  const validTypes = ['text', 'number', 'enum', 'percent'];
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const empty = value => value === null || value === undefined || value === '';
  const numeric = field => field && (field.type === 'number' || field.type === 'percent');
  const lookup = (fieldDefs, id) => (fieldDefs || fields).find(field => field.id === id);
  const normalize = value => String(value).toLocaleLowerCase('ru').trim();
  const numericInput = value => {
    if (finite(value)) return value;
    if (typeof value !== 'string' || value.trim() === '') return null;
    const parsed = Number(value.trim().replace(/\s/g, '').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
  };

  function evaluateRule(row, rule, fieldDefs) {
    if (!row || !rule || !ops.includes(rule.op)) return false;
    const field = lookup(fieldDefs, rule.field);
    if (!field) return false;
    const actual = row[field.id];
    if (rule.op === 'empty') return empty(actual);
    if (rule.op === 'notEmpty') return !empty(actual);
    // Missing values match only explicit emptiness conditions, including for neq.
    if (empty(actual)) return false;
    let a, b, c;
    if (numeric(field)) {
      if (!finite(actual)) return false;
      a = actual; b = numericInput(rule.value); c = numericInput(rule.value2);
      if (b === null) return false;
    } else {
      if (typeof actual !== 'string' || empty(rule.value)) return false;
      a = normalize(actual); b = normalize(rule.value); c = empty(rule.value2) ? null : normalize(rule.value2);
    }
    switch (rule.op) {
      case 'contains': return !numeric(field) && a.includes(b);
      case 'notContains': return !numeric(field) && !a.includes(b);
      case 'eq': return numeric(field) ? a === b : collator.compare(a, b) === 0;
      case 'neq': return numeric(field) ? a !== b : collator.compare(a, b) !== 0;
      case 'gt': return numeric(field) && a > b;
      case 'gte': return numeric(field) && a >= b;
      case 'lt': return numeric(field) && a < b;
      case 'lte': return numeric(field) && a <= b;
      case 'between': return numeric(field) && c !== null && a >= b && a <= c;
      default: return false;
    }
  }

  function filterRows(inputRows, filters, mode, search, fieldDefs) {
    const defs = fieldDefs || fields;
    const conditions = Array.isArray(filters) ? filters : [];
    // An unknown condition must never accidentally broaden a saved view.
    if (conditions.some(rule => !rule || !lookup(defs, rule.field) || !ops.includes(rule.op))) return [];
    const terms = String(search || '').trim().toLocaleLowerCase('ru').split(/\s+/).filter(Boolean);
    return inputRows.filter(row => {
      const matches = !conditions.length || (mode === 'or' ? conditions.some(rule => evaluateRule(row, rule, defs)) : conditions.every(rule => evaluateRule(row, rule, defs)));
      if (!matches) return false;
      if (!terms.length) return true;
      const searchable = defs.map(field => empty(row[field.id]) ? '' : String(row[field.id])).join(' ').toLocaleLowerCase('ru');
      return terms.every(term => searchable.includes(term));
    });
  }

  function sortRows(inputRows, sorts, fieldDefs) {
    const defs = fieldDefs || fields;
    const active = (sorts || []).filter(sort => sort && lookup(defs, sort.field));
    return inputRows.map((row, index) => ({ row, index })).sort((left, right) => {
      for (const sort of active) {
        const field = lookup(defs, sort.field);
        const a = left.row[field.id], b = right.row[field.id];
        const aEmpty = empty(a) || (numeric(field) && !finite(a));
        const bEmpty = empty(b) || (numeric(field) && !finite(b));
        if (aEmpty && bEmpty) continue;
        if (aEmpty) return 1;
        if (bEmpty) return -1;
        const comparison = numeric(field) ? a - b : collator.compare(String(a), String(b));
        if (comparison) return (sort.direction === 'desc' ? -1 : 1) * comparison;
      }
      return collator.compare(String(left.row.id || ''), String(right.row.id || '')) || left.index - right.index;
    }).map(item => item.row);
  }

  function groupRows(inputRows, groups, fieldDefs) {
    const defs = fieldDefs || fields;
    const active = [...new Set((groups || []).map(group => typeof group === 'string' ? group : group && group.field).filter(id => lookup(defs, id)))].slice(0, 3);
    if (!active.length) return [];
    function build(source, depth, path) {
      const field = active[depth], buckets = new Map();
      source.forEach(row => {
        const value = empty(row[field]) ? null : row[field];
        const key = JSON.stringify([typeof value, value]);
        if (!buckets.has(key)) buckets.set(key, { value, rows: [] });
        buckets.get(key).rows.push(row);
      });
      return [...buckets.values()].map(bucket => {
        const nextPath = path.concat([[field, bucket.value]]);
        return { key: JSON.stringify(nextPath), field, value: bucket.value, rows: bucket.rows, children: depth + 1 < active.length ? build(bucket.rows, depth + 1, nextPath) : [] };
      });
    }
    return build(inputRows, 0, []);
  }

  function aggregationModes(fieldId, fieldDefs) {
    const field = lookup(fieldDefs, fieldId);
    if (!field) return [];
    if (!numeric(field)) return ['count'];
    if (fieldId === 'margin') return ['weighted', 'min', 'max', 'count'];
    if (fieldId === 'coverage') return ['weighted', 'avg', 'min', 'max', 'count'];
    if (fieldId === 'cost') return ['avg', 'min', 'max', 'count'];
    return ['sum', 'avg', 'min', 'max', 'count'];
  }

  function aggregate(inputRows, fieldId, mode, fieldDefs) {
    const defs = fieldDefs || fields, field = lookup(defs, fieldId), total = inputRows.length;
    const allowed = aggregationModes(fieldId, defs);
    const selected = allowed.includes(mode) ? mode : allowed[0] || 'count';
    const base = { value: null, known: 0, total, partial: total > 0, mode: selected };
    if (!field) return Object.assign(base, { label: 'Поле недоступно' });
    const knownRows = inputRows.filter(row => numeric(field) ? finite(row[fieldId]) : !empty(row[fieldId]));
    let known = knownRows.length, value = null;
    if (selected === 'weighted' && fieldId === 'margin') {
      const complete = inputRows.filter(row => finite(row.profit) && finite(row.revenue) && row.revenue >= 0);
      const denominator = complete.reduce((sum, row) => sum + row.revenue, 0);
      known = complete.length;
      value = denominator > 0 ? complete.reduce((sum, row) => sum + row.profit, 0) / denominator * 100 : null;
    } else if (selected === 'weighted' && fieldId === 'coverage') {
      const complete = inputRows.filter(row => finite(row.stock) && finite(row.sales) && row.stock >= 0 && row.sales >= 0);
      const denominator = complete.reduce((sum, row) => sum + row.sales, 0);
      known = complete.length;
      value = denominator > 0 ? complete.reduce((sum, row) => sum + row.stock, 0) / denominator * 30 : null;
    } else if (selected === 'count') {
      value = known;
    } else if (known) {
      const values = knownRows.map(row => row[fieldId]);
      if (selected === 'sum') value = values.reduce((sum, item) => sum + item, 0);
      if (selected === 'avg') value = values.reduce((sum, item) => sum + item, 0) / known;
      if (selected === 'min') value = Math.min(...values);
      if (selected === 'max') value = Math.max(...values);
    }
    const labels = { sum: 'Сумма', avg: 'Среднее', min: 'Минимум', max: 'Максимум', count: 'Заполнено', weighted: fieldId === 'margin' ? 'Взвешенная маржа' : 'Запас по темпу продаж' };
    return { value, known, total, partial: known < total, mode: selected, label: labels[selected] };
  }

  const defaultVisible = ['name', 'brand', 'owner', 'status', 'sales', 'revenue', 'stock', 'coverage'];
  function makeColumns(visible) {
    return fields.filter(field => field.id !== 'id').map(field => ({
      id: field.id, width: field.id === 'name' ? 300 : field.id === 'note' ? 220 : field.id === 'status' ? 150 : field.id === 'revenue' || field.id === 'profit' ? 155 : 132,
      hidden: !(visible || defaultVisible).includes(field.id), pinned: field.id === 'name', color: null, format: null, aggregate: null,
    }));
  }
  function preset(id, name, extra) {
    return Object.assign({ id, name, icon: 'table', columns: makeColumns(), sorts: [], groups: [], filters: [], filterMode: 'and', rules: [], density: 'normal', rowLines: true, zebra: false, search: '', customFields: [] }, extra || {});
  }
  const presets = [
    preset('all', 'Все товары'),
    preset('brands', 'По брендам', { icon: 'group', groups: ['brand', 'category'], sorts: [{ field: 'revenue', direction: 'desc' }] }),
    preset('stock', 'Контроль остатков', {
      icon: 'stock', columns: makeColumns(['name', 'brand', 'owner', 'sales', 'stock', 'coverage', 'note']),
      filters: [{ field: 'coverage', op: 'lt', value: 14 }], sorts: [{ field: 'coverage', direction: 'asc' }],
      rules: [{ id: 'stock-low', field: 'coverage', op: 'lt', value: 7, color: '#fef3c7', target: 'cell', targetField: 'coverage', enabled: true }],
    }),
    preset('economics', 'Экономика', {
      icon: 'chart', columns: makeColumns(['name', 'brand', 'sales', 'revenue', 'cost', 'profit', 'margin']),
      sorts: [{ field: 'profit', direction: 'desc' }],
      rules: [{ id: 'missing-cost', field: 'cost', op: 'empty', color: '#fee2e2', target: 'cell', targetField: 'cost', enabled: true }],
    }),
  ];

  function sanitizeView(input, role, fieldDefs) {
    const source = input && typeof input === 'object' ? input : {};
    const incompatibilities = [];
    const roleName = role === 'manager' ? 'manager' : 'owner';
    const issue = (section, field, reason, index) => incompatibilities.push({ section, field, reason, index });
    const baseDefs = fieldDefs || fields;
    const seenCustom = new Set(fields.map(field => field.id));
    const customFields = (Array.isArray(source.customFields) ? source.customFields : []).filter((field, index) => {
      if (!field || !/^custom_[a-zA-Z0-9_-]+$/.test(field.id) || seenCustom.has(field.id) || !validTypes.includes(field.type)) {
        issue('customFields', field && field.id, 'invalid_field', index); return false;
      }
      seenCustom.add(field.id); return true;
    }).map(field => ({ id: field.id, label: String(field.label || 'Новое поле').slice(0, 80), type: field.type, editable: true, financial: !!field.financial, options: Array.isArray(field.options) ? field.options.map(String).slice(0, 100) : [] }));
    const defs = baseDefs.concat(customFields.filter(field => !lookup(baseDefs, field.id)));
    const accessible = id => {
      const field = lookup(defs, id);
      const original = lookup(fields, id);
      return !!field && !(roleName === 'manager' && (field.financial || (original && original.financial)));
    };
    const check = (section, id, index) => {
      if (accessible(id)) return true;
      issue(section, id, lookup(defs, id) ? 'forbidden_field' : 'unknown_field', index); return false;
    };
    const hexColor = color => typeof color === 'string' && /^#[\da-f]{6}$/i.test(color) ? color : null;
    const seenColumns = new Set();
    const columns = (Array.isArray(source.columns) ? source.columns : makeColumns()).filter((column, index) => {
      if (!column || !check('columns', column.id, index) || seenColumns.has(column.id)) return false;
      seenColumns.add(column.id); return true;
    }).map(column => ({ id: column.id, width: Math.max(80, Math.min(600, Number(column.width) || 132)), hidden: !!column.hidden, pinned: !!column.pinned, color: hexColor(column.color), format: typeof column.format === 'string' ? column.format.slice(0, 40) : null, aggregate: aggregationModes(column.id, defs).includes(column.aggregate) ? column.aggregate : null }));
    // Keep unmentioned fields available in the fields panel, but hidden.
    defs.forEach(field => { if (field.id !== 'id' && accessible(field.id) && !seenColumns.has(field.id)) columns.push({ id: field.id, width: 132, hidden: true, pinned: false, color: null, format: null, aggregate: null }); });
    function conditions(section) {
      return (Array.isArray(source[section]) ? source[section] : []).filter((condition, index) => {
        if (!condition || !check(section, condition.field, index)) return false;
        if (!ops.includes(condition.op)) { issue(section, condition.field, 'invalid_operator', index); return false; }
        if (section === 'rules' && condition.targetField && !check(section, condition.targetField, index)) return false;
        return true;
      }).map((condition, index) => {
        const result = { field: condition.field, op: condition.op, value: condition.value, value2: condition.value2 };
        if (section === 'rules') Object.assign(result, { id: String(condition.id || 'rule-' + index), color: hexColor(condition.color) || '#fef3c7', target: condition.target === 'row' ? 'row' : 'cell', targetField: condition.targetField || condition.field, enabled: condition.enabled !== false });
        return result;
      });
    }
    const filters = conditions('filters'), rules = conditions('rules');
    const sorts = (Array.isArray(source.sorts) ? source.sorts : []).filter((sort, index) => sort && check('sorts', sort.field, index)).map(sort => ({ field: sort.field, direction: sort.direction === 'desc' ? 'desc' : 'asc' }));
    const groups = [...new Set((Array.isArray(source.groups) ? source.groups : []).map(group => typeof group === 'string' ? group : group && group.field).filter((id, index) => check('groups', id, index)))].slice(0, 3);
    const allowedCustomFields = customFields.filter(field => accessible(field.id));
    const blocked = incompatibilities.some(item => item.section === 'filters');
    return {
      id: String(source.id || 'custom'), name: String(source.name || 'Новое представление').slice(0, 100), icon: typeof source.icon === 'string' ? source.icon : 'table',
      columns, sorts, groups, filters, filterMode: source.filterMode === 'or' ? 'or' : 'and', rules,
      density: ['normal', 'compact', 'comfortable'].includes(source.density) ? source.density : 'normal',
      rowLines: source.rowLines !== false, zebra: !!source.zebra, search: String(source.search || '').slice(0, 500),
      customFields: allowedCustomFields, incompatibilities, blocked,
    };
  }

  return { fields, rows, presets, ops, filterRows, sortRows, groupRows, aggregate, aggregationModes, evaluateRule, sanitizeView, makeColumns };
});
