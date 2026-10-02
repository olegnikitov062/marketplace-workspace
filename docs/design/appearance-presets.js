/* Appearance snapshots only. Sharing here is a browser-local demonstration. */
'use strict';
window.AppearancePresets = (() => {
  const STORAGE_KEY = 'mw-appearance-v1';
  const privateField = id => /^(custom_|private-)/.test(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  const role = profile => profile === 'owner' ? 'Руководитель' : 'Менеджер';
  const color = value => typeof value === 'string' && /^#[\da-f]{6}$/i.test(value) ? value : '';
  const scalar = value => typeof value === 'string' ? value.slice(0, 2000)
    : typeof value === 'number' && Number.isFinite(value) ? value
    : typeof value === 'boolean' ? value : null;
  let context, dialog, opener, openerSelector, state = { schema: 1, presets: [] };
  let editor = null, feedback = '', feedbackError = false;

  // Never serialize an entire saved view or a table row, even if an adapter supplies one.
  function appearance(source, scope) {
    if (!source || typeof source !== 'object' || !Array.isArray(source.columns)) {
      throw new Error('Не удалось прочитать текущее оформление таблицы.');
    }
    const allowField = id => typeof id === 'string' && id.length > 0
      && (scope !== 'team' || !privateField(id));
    const result = {
      density: ['compact', 'normal', 'comfortable'].includes(source.density) ? source.density : 'normal',
      zebra: source.zebra === true,
      rowLines: source.rowLines !== false,
      columns: source.columns.filter(column => column && allowField(column.id)).map(column => {
        const item = { id: column.id, color: color(column.color) };
        if (typeof column.format === 'string') item.format = column.format.slice(0, 40);
        return item;
      })
    };
    if (typeof source.highlight === 'boolean') result.highlight = source.highlight;
    if (Array.isArray(source.rules)) {
      result.rules = source.rules.filter(rule => rule && allowField(rule.field)
        && (!rule.targetField || allowField(rule.targetField))).map((rule, index) => ({
        id: typeof rule.id === 'string' ? rule.id : 'appearance-rule-' + index,
        field: rule.field,
        op: typeof rule.op === 'string' ? rule.op : 'eq',
        value: scalar(rule.value),
        value2: scalar(rule.value2),
        color: color(rule.color),
        target: rule.target === 'row' ? 'row' : 'cell',
        targetField: rule.targetField || rule.field,
        enabled: rule.enabled !== false
      }));
    }
    return result;
  }

  function notice(message, error = false) {
    feedback = message;
    feedbackError = error;
    const target = dialog?.querySelector('#appearance-feedback');
    if (target) {
      target.textContent = message;
      target.classList.toggle('is-error', error);
      target.hidden = !message;
    }
  }

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const next = raw === null ? { schema: 1, presets: [] } : JSON.parse(raw);
      if (next?.schema !== 1 || !Array.isArray(next.presets)) {
        throw new Error('unsupported state');
      }
      state = next;
      return true;
    } catch {
      notice('Не удалось прочитать пресеты в этом браузере. Сохранение и изменения не выполнены.', true);
      return false;
    }
  }

  function visible(preset) {
    return preset && preset.tableId === context.tableId
      && ['owner', 'manager'].includes(preset.author)
      && typeof preset.id === 'string' && typeof preset.name === 'string'
      && (preset.scope === 'team' || (preset.scope === 'personal' && preset.author === context.profile));
  }

  function currentPreset(id, requireAuthor = false) {
    if (!readState()) return null;
    const preset = state.presets.find(item => item?.id === id && visible(item));
    if (!preset) {
      editor = null;
      notice('Этот пресет удалён или больше недоступен. Список обновлён.', true);
      render();
      return null;
    }
    if (requireAuthor && preset.author !== context.profile) {
      notice('Изменять пресет может только его автор.', true);
      return null;
    }
    return preset;
  }

  function writeState(next, message) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      notice('Браузер не сохранил изменение. Проверьте доступ к хранилищу и повторите.', true);
      return false;
    }
    state = next;
    editor = null;
    notice(message);
    render();
    context.toast?.(message);
    return true;
  }

  function validateName(value) {
    const name = value.trim();
    if (!name || name.length > 60) {
      notice('Укажите название от 1 до 60 символов.', true);
      return null;
    }
    return name;
  }

  function button(action, label, id = '', classes = '') {
    return `<button type="button" class="btn ${classes}" data-appearance-action="${action}"
      ${id ? `data-preset-id="${escape(id)}"` : ''}>${label}</button>`;
  }

  function preview(preset) {
    const columns = Array.isArray(preset.config?.columns) ? preset.config.columns : [];
    const rules = Array.isArray(preset.config?.rules) ? preset.config.rules : [];
    const colors = [...new Set([
      ...columns.map(item => color(item?.color)),
      ...rules.map(item => color(item?.color))
    ].filter(Boolean))].slice(0, 7);
    const density = { compact: 'Компактно', normal: 'Обычно', comfortable: 'Свободно' }[preset.config?.density] || 'Обычно';
    return `<div class="appearance-preview" aria-label="${escape(density)}${colors.length ? ', цвета оформления' : ', без цветовых акцентов'}">
      <span class="appearance-swatches" aria-hidden="true">${colors.length
        ? colors.map(tint => `<i style="--preset-color:${tint}"></i>`).join('')
        : '<i class="is-neutral"></i>'}</span><span>${density}${preset.config?.zebra ? ' · полосы' : ''}</span>
    </div>`;
  }

  function card(preset) {
    const mine = preset.author === context.profile;
    return `<article class="appearance-card">
      <div class="appearance-card-heading"><h3>${escape(preset.name)}</h3>
        <span class="appearance-scope">${preset.scope === 'team' ? 'Для команды' : 'Только мне'}</span></div>
      <p class="appearance-meta">${role(preset.author)}${mine ? ' · вы автор' : ''}</p>
      ${preview(preset)}
      <div class="appearance-card-actions">${button('apply', 'Применить', preset.id, 'primary')}
        ${mine ? button('update', 'Обновить из текущего', preset.id)
          + button('rename', 'Переименовать', preset.id)
          + button('delete', 'Удалить', preset.id) : ''}</div>
    </article>`;
  }

  function libraryHTML() {
    const presets = state.presets.filter(visible);
    const personal = presets.filter(preset => preset.scope === 'personal');
    const team = presets.filter(preset => preset.scope === 'team');
    return `<div class="appearance-intro">Применение меняет только ваше оформление.
      Оформление сохранится в текущем личном виде. Данные, фильтры, сортировки, состав полей и расчёты сохраняются.</div>
      <section class="appearance-section" aria-labelledby="appearance-personal-title">
        <h3 id="appearance-personal-title">Мои пресеты <span>${personal.length}</span></h3>
        <div class="appearance-list">${personal.map(card).join('') || '<p class="appearance-empty">Личных пресетов пока нет. Сохраните текущее оформление ниже.</p>'}</div>
      </section>
      <section class="appearance-section" aria-labelledby="appearance-team-title">
        <h3 id="appearance-team-title">Общие пресеты <span>${team.length}</span></h3>
        <p class="appearance-hint">Доступны всей команде. Каждый применяет пресет сам; обновление не меняет оформление коллег.</p>
        <div class="appearance-list">${team.map(card).join('') || '<p class="appearance-empty">Общих пресетов пока нет. Выберите «Для команды» при сохранении.</p>'}</div>
      </section>
      <form class="appearance-save" data-appearance-form="create">
        <h3>Сохранить текущее оформление</h3>
        <label for="appearance-name">Название</label>
        <input id="appearance-name" name="name" maxlength="60" required autocomplete="off" placeholder="Например, Утренний контроль">
        <label for="appearance-scope">Кому доступен</label>
        <select id="appearance-scope" name="scope"><option value="personal">Только мне</option><option value="team">Для команды</option></select>
        <p class="appearance-hint">Личные поля и правила по ним не включаются в общий пресет.</p>
        <button class="btn primary" type="submit">Сохранить пресет</button>
      </form>`;
  }

  function editorHTML() {
    const preset = state.presets.find(item => item?.id === editor.id && visible(item));
    if (!preset) {
      editor = null;
      notice('Этот пресет удалён или больше недоступен. Список обновлён.', true);
      return libraryHTML();
    }
    const title = escape(preset.name);
    if (editor.type === 'rename') {
      return `<form class="appearance-save" data-appearance-form="rename"><h3>Переименовать «${title}»</h3>
        <label for="appearance-rename">Новое название</label><input id="appearance-rename" name="name" maxlength="60"
          required autocomplete="off" value="${title}"><div class="appearance-card-actions">
          <button class="btn primary" type="submit">Сохранить название</button>${button('back', 'Отмена')}</div></form>`;
    }
    if (editor.type === 'delete') {
      return `<div class="appearance-confirm"><h3>Удалить «${title}»?</h3><p>Пресет исчезнет из списка${preset.scope === 'team' ? ' всей команды' : ''}.
        Уже применённое оформление и данные таблиц сохранятся.</p><div class="appearance-card-actions">
        ${button('confirm-delete', 'Удалить пресет', preset.id, 'appearance-danger')}${button('back', 'Отмена')}</div></div>`;
    }
    return `<div class="appearance-confirm"><h3>Обновить «${title}»?</h3><p>Текущее оформление заменит сохранённый снимок в этом пресете.
      Уже применённые копии не изменятся.${preset.scope === 'team' ? ' Личные поля и правила по ним не включаются.' : ''}</p>
      <div class="appearance-card-actions">${button('confirm-update', 'Обновить пресет', preset.id, 'primary')}${button('back', 'Отмена')}</div></div>`;
  }

  function render(preserveInputs = true) {
    if (!dialog || !context) return;
    const values = preserveInputs ? [...dialog.querySelectorAll('input, select')].map(node => [node.id, node.value]) : [];
    const focused = dialog.contains(document.activeElement) ? document.activeElement : null;
    const focusId = focused?.id;
    const focusAction = focused?.dataset.appearanceAction;
    const focusPreset = focused?.dataset.presetId;
    const selection = focused?.tagName === 'INPUT' ? [focused.selectionStart, focused.selectionEnd] : null;
    const scroll = dialog.querySelector('.drawer-body')?.scrollTop || 0;
    const content = editor ? editorHTML() : libraryHTML();
    dialog.innerHTML = `<div class="drawer-head"><div><h2 id="appearance-title">Пресеты для таблицы «${escape(context.label)}»</h2>
        <p class="appearance-hint">${role(context.profile)} · оформление</p></div>
      <button type="button" class="icon-button" data-appearance-action="close" aria-label="Закрыть пресеты">×</button></div>
      <div class="drawer-body"><p id="appearance-feedback" class="appearance-feedback ${feedbackError ? 'is-error' : ''}"
        role="status" aria-live="polite" ${feedback ? '' : 'hidden'}>${escape(feedback)}</p>${content}</div>
      <div class="drawer-foot"><span class="appearance-hint">Демонстрация · пресеты хранятся в этом браузере</span>${button('close', 'Закрыть')}</div>`;
    values.forEach(([id, value]) => {
      const node = dialog.querySelector('#' + CSS.escape(id));
      if (node) node.value = value;
    });
    dialog.querySelector('.drawer-body').scrollTop = scroll;
    const next = focusId ? dialog.querySelector('#' + CSS.escape(focusId))
      : focusAction ? [...dialog.querySelectorAll('[data-appearance-action]')].find(node =>
        node.dataset.appearanceAction === focusAction && node.dataset.presetId === focusPreset) : null;
    if (next) {
      next.focus({ preventScroll: true });
      if (selection && selection[0] !== null) next.setSelectionRange(...selection);
    } else if (dialog.open && focused) {
      (dialog.querySelector('#appearance-rename') || dialog.querySelector('[data-appearance-action="back"]')
        || dialog.querySelector('[data-appearance-action="close"]')).focus({ preventScroll: true });
    }
  }

  function create(form) {
    const name = validateName(form.elements.name.value);
    if (!name || !readState()) return;
    const scope = form.elements.scope.value === 'team' ? 'team' : 'personal';
    let config;
    try { config = appearance(context.capture(), scope); }
    catch (error) { notice(error.message || 'Не удалось прочитать оформление.', true); return; }
    const id = typeof globalThis.crypto?.randomUUID === 'function' ? globalThis.crypto.randomUUID()
      : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    const preset = { id, tableId: context.tableId, scope, author: context.profile, name, config, updatedAt: new Date().toISOString() };
    if (writeState({ schema: 1, presets: [...state.presets, preset] }, 'Пресет сохранён.')) {
      dialog.querySelector('#appearance-name').value = '';
      dialog.querySelector('#appearance-name').focus();
    }
  }

  function act(action, id) {
    if (action === 'close') { dialog.close(); return; }
    if (action === 'back') { editor = null; render(false); return; }
    const preset = currentPreset(id, action !== 'apply');
    if (!preset) return;
    if (action === 'apply') {
      try {
        if (context.apply(appearance(preset.config, preset.scope), { scope: preset.scope }) === false) {
          notice('Не удалось применить оформление. Пресет не изменён.', true);
          return;
        }
        notice('Применён пресет «' + preset.name + '». Изменилось только ваше оформление.');
        context.toast?.('Оформление применено: ' + preset.name);
      } catch { notice('Не удалось применить оформление. Проверьте доступные поля таблицы.', true); }
      return;
    }
    if (['rename', 'delete', 'update'].includes(action)) {
      editor = { type: action, id };
      notice('');
      render(false);
      dialog.querySelector('#appearance-rename')?.focus();
      return;
    }
    if (action === 'confirm-delete') {
      writeState({ schema: 1, presets: state.presets.filter(item => item.id !== id) }, 'Пресет удалён.');
      return;
    }
    if (action === 'confirm-update') {
      let config;
      try { config = appearance(context.capture(), preset.scope); }
      catch (error) { notice(error.message || 'Не удалось прочитать оформление.', true); return; }
      const updated = { ...preset, config, updatedAt: new Date().toISOString() };
      writeState({ schema: 1, presets: state.presets.map(item => item.id === id ? updated : item) }, 'Пресет обновлён. Применённые копии не изменились.');
    }
  }

  function ensureDialog() {
    if (dialog) return;
    dialog = document.createElement('dialog');
    dialog.id = 'appearance-dialog';
    dialog.className = 'modal';
    dialog.setAttribute('aria-labelledby', 'appearance-title');
    document.body.append(dialog);
    dialog.addEventListener('click', event => {
      const node = event.target.closest('[data-appearance-action]');
      if (node) act(node.dataset.appearanceAction, node.dataset.presetId);
    });
    dialog.addEventListener('submit', event => {
      const form = event.target.closest('[data-appearance-form]');
      if (!form) return;
      event.preventDefault();
      if (form.dataset.appearanceForm === 'create') { create(form); return; }
      const name = validateName(form.elements.name.value);
      if (!name || !editor) return;
      const preset = currentPreset(editor.id, true);
      if (!preset) return;
      const updated = { ...preset, name, updatedAt: new Date().toISOString() };
      writeState({ schema: 1, presets: state.presets.map(item => item.id === preset.id ? updated : item) }, 'Название пресета сохранено.');
    });
    dialog.addEventListener('close', () => {
      const target = opener?.isConnected ? opener : openerSelector ? document.querySelector(openerSelector) : null;
      if (target && !target.closest('[inert]')) target.focus({ preventScroll: true });
      else document.querySelector('main')?.focus({ preventScroll: true });
    });
  }

  window.addEventListener('storage', event => {
    if (!dialog?.open || (event.key !== STORAGE_KEY && event.key !== null)) return;
    const previousIds = state.presets.filter(visible).map(preset => preset.id);
    if (readState()) {
      const removed = previousIds.some(id => !state.presets.some(preset => preset?.id === id && visible(preset)));
      notice(removed ? 'В другой вкладке удалён пресет. Список обновлён; ваше оформление сохранилось.'
        : 'Список пресетов обновлён в другой вкладке. Ваше оформление не изменилось.');
    }
    render();
  });

  function open(options) {
    if (!['products', 'purchases'].includes(options?.tableId)
      || !['owner', 'manager'].includes(options.profile)
      || typeof options.capture !== 'function' || typeof options.apply !== 'function') {
      throw new Error('Для пресетов нужны таблица, профиль и адаптеры оформления.');
    }
    ensureDialog();
    opener = document.activeElement;
    openerSelector = null;
    if (opener?.id) openerSelector = '#' + CSS.escape(opener.id);
    else if (opener) {
      const selectors = [...opener.attributes].filter(attribute => attribute.name.startsWith('data-'))
        .map(attribute => `[${attribute.name}="${CSS.escape(attribute.value)}"]`);
      if (selectors.length) openerSelector = selectors.join('');
    }
    context = options;
    editor = null;
    notice('');
    readState();
    render(false);
    if (!dialog.open) dialog.showModal();
  }

  return { open };
})();
