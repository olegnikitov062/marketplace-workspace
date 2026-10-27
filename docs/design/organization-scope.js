/* Synthetic organization/cabinet scope for the local prototype. No remote access. */
(function (root) {
  'use strict';

  const organizations = [
    { id: 'primary', name: 'Демо · Атлас', shortName: 'Атлас' },
    { id: 'secondary', name: 'Демо · Север', shortName: 'Север' },
  ];
  const cabinets = [
    { id: 'wb-main', organizationId: 'primary', marketplace: 'WB', label: 'WB · Основной' },
    { id: 'wb-shop', organizationId: 'primary', marketplace: 'WB', label: 'WB · Магазин' },
    { id: 'ozon-main', organizationId: 'primary', marketplace: 'Ozon', label: 'Ozon · Основной' },
    { id: 'wb-north', organizationId: 'secondary', marketplace: 'WB', label: 'WB · Север' },
    { id: 'ozon-north', organizationId: 'secondary', marketplace: 'Ozon', label: 'Ozon · Север' },
  ];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const cabinetCount = count => `${count} ${count === 1 ? 'кабинет' : count >= 2 && count <= 4 ? 'кабинета' : 'кабинетов'}`;
  const memory = new Map();
  let profile = 'owner', selected = ['wb-main', 'wb-shop', 'ozon-main'], pending = [];
  let onChange = null, dialog = null, switchButton = null, contextElement = null, catalog = null;
  let storageUnavailable = false;

  function allowed() { return cabinets.filter(cabinet => profile === 'owner' || cabinet.organizationId === 'primary'); }
  function normalize(values) {
    const ids = new Set(Array.isArray(values) ? values : []);
    return allowed().filter(cabinet => ids.has(cabinet.id)).map(cabinet => cabinet.id);
  }
  function defaults() { return allowed().filter(cabinet => cabinet.organizationId === 'primary').map(cabinet => cabinet.id); }
  function selection() { return selected.slice(); }
  function selectedOrganizations(ids = selected) {
    const chosen = new Set(ids);
    const organizationIds = new Set(cabinets.filter(cabinet => chosen.has(cabinet.id)).map(cabinet => cabinet.organizationId));
    return organizations.filter(organization => organizationIds.has(organization.id));
  }
  function singleOrganization() {
    const list = selectedOrganizations();
    return list.length === 1 ? list[0].id : null;
  }
  function isCombined() { return selectedOrganizations().length > 1; }
  function contextKey() {
    const id = singleOrganization();
    return id === 'primary' ? '' : id === 'secondary' ? ':org:secondary' : ':combined';
  }
  function organizationName(id) { return organizations.find(organization => organization.id === id)?.name || ''; }
  function ensureCatalog() {
    if (catalog) return catalog;
    const source = root.GridEngine?.rows;
    if (!Array.isArray(source)) throw new Error('OrganizationScope requires GridEngine.rows.');
    const decorate = (row, cabinet, id) => ({ ...row, id, organizationId: cabinet.organizationId,
      organization: organizationName(cabinet.organizationId), cabinetId: cabinet.id,
      marketplace: cabinet.marketplace, cabinet: cabinet.label });
    const primary = source.map((row, index) => decorate(row, cabinets[Math.floor(index / 4) % 3], row.id));
    const secondary = source.slice(0, 18).map((row, index) => decorate(row, cabinets[3 + Math.floor(index / 3) % 2], 'secondary:' + row.id));
    catalog = primary.concat(secondary);
    return catalog;
  }
  function allRows() { return ensureCatalog().slice(); }
  function catalogFor(organizationId) { return ensureCatalog().filter(row => row.organizationId === organizationId); }
  function scopedRows() {
    const chosen = new Set(selected);
    return ensureCatalog().filter(row => chosen.has(row.cabinetId));
  }
  function label() {
    const list = selectedOrganizations();
    return list.length === 1 ? list[0].shortName : `${list.length} организации`;
  }
  function describe() {
    const list = cabinets.filter(cabinet => selected.includes(cabinet.id));
    return list.length <= 3 ? list.map(cabinet => cabinet.label).join(' + ')
      : `${cabinetCount(list.length)} · ${[...new Set(list.map(cabinet => cabinet.marketplace))].join(' и ')}`;
  }
  function load() {
    storageUnavailable = false;
    let values = memory.get(profile);
    if (!values) {
      try {
        const raw = root.localStorage.getItem('mw-organization-scope-v1:' + profile);
        if (raw) {
          try {
            const saved = JSON.parse(raw);
            if (saved?.schemaVersion === 1) values = saved.selected;
          } catch { /* Invalid local settings fall back to the accessible default. */ }
        }
      } catch { storageUnavailable = true; }
    }
    selected = normalize(values);
    if (!selected.length) selected = defaults();
    memory.set(profile, selection());
  }
  function persist() {
    memory.set(profile, selection());
    try {
      root.localStorage.setItem('mw-organization-scope-v1:' + profile, JSON.stringify({ schemaVersion: 1, selected }));
      storageUnavailable = false;
    } catch { storageUnavailable = true; }
  }
  function focus() { document.getElementById('organization-switch')?.focus({ preventScroll: true }); }
  function renderHeader() {
    const button = document.getElementById('organization-switch');
    if (button) {
      button.innerHTML = `<span>${escape(label())}<small>${escape(cabinetCount(selected.length))}</small></span><span aria-hidden="true">⌄</span>`;
      button.setAttribute('aria-label', 'Выбрать организации и кабинеты');
      button.setAttribute('aria-haspopup', 'dialog');
      button.setAttribute('aria-expanded', String(Boolean(dialog?.open)));
      button.setAttribute('title', `${selectedOrganizations().map(organization => organization.name).join(' + ')} · ${describe()}`);
      if (button !== switchButton) {
        switchButton?.removeEventListener('click', open);
        switchButton = button;
        button.addEventListener('click', open);
      }
    }
    const context = document.getElementById('organization-context');
    if (context) {
      context.innerHTML = `<span class="org-context-mode${isCombined() ? ' is-combined' : ''}">${isCombined() ? 'Общий просмотр' : 'Одна организация'}</span><span class="org-context-copy">${escape(describe())}${isCombined() ? '<span class="org-context-hint">Редактирование — внутри одной организации</span>' : ''}</span><button type="button" class="btn" data-org-open>Изменить</button>${storageUnavailable ? '<span class="org-storage-status" role="status">Выбор действует до закрытия страницы: браузер не сохранил настройки.</span>' : ''}`;
      if (context !== contextElement) {
        contextElement?.removeEventListener('click', handleContextClick);
        contextElement = context;
        context.addEventListener('click', handleContextClick);
      }
    }
  }
  function handleContextClick(event) { if (event.target.closest('[data-org-open]')) open(); }
  function close() { if (dialog?.open) dialog.close(); }
  function apply(values) {
    const next = normalize(values);
    if (!next.length) return false;
    const previous = selection();
    const changed = previous.join('|') !== next.join('|');
    selected = next;
    persist();
    close();
    renderHeader();
    if (changed && typeof onChange === 'function') onChange({ previous, next: selection() });
    return true;
  }
  function chooseOrganization(id) { return apply(allowed().filter(cabinet => cabinet.organizationId === id).map(cabinet => cabinet.id)); }
  function syncPending() {
    if (!dialog) return;
    dialog.querySelectorAll('[data-org-cabinet]').forEach(input => { input.checked = pending.includes(input.dataset.orgCabinet); });
    dialog.querySelectorAll('[data-org-choice]').forEach(input => {
      const group = allowed().filter(cabinet => cabinet.organizationId === input.dataset.orgChoice);
      const count = group.filter(cabinet => pending.includes(cabinet.id)).length;
      input.checked = count === group.length;
      input.indeterminate = count > 0 && count < group.length;
    });
    const count = selectedOrganizations(pending).length;
    const summary = dialog.querySelector('#organization-selection-summary');
    summary.textContent = pending.length ? `${count === 1 ? 'Одна организация' : count + ' организации'} · ${cabinetCount(pending.length)}` : 'Выберите хотя бы один кабинет';
    dialog.querySelector('#organization-selection-mode').textContent = count > 1
      ? 'Данные выбранных кабинетов будут показаны вместе. Для редактирования откройте одну организацию.'
      : 'Внутри одной организации данные выбранных кабинетов можно просматривать и редактировать в рамках ваших прав.';
    dialog.querySelector('[data-org-action="apply"]').disabled = !pending.length;
  }
  function renderDialog() {
    const available = allowed();
    dialog.innerHTML = `<div class="drawer-head"><div><h2 id="organization-dialog-title">Организации и кабинеты</h2><p class="muted">Выберите, какие данные показать в рабочем пространстве</p></div><button type="button" class="icon-button" data-org-action="close" aria-label="Закрыть выбор организаций">×</button></div>
      <div class="drawer-body org-dialog-body"><div class="org-shortcuts" role="group" aria-label="Быстрый выбор кабинетов"><button type="button" class="btn" data-org-marketplace="all">Все доступные</button><button type="button" class="btn" data-org-marketplace="WB">WB</button><button type="button" class="btn" data-org-marketplace="Ozon">Ozon</button></div>
      ${organizations.filter(organization => available.some(cabinet => cabinet.organizationId === organization.id)).map(organization => {
        const group = available.filter(cabinet => cabinet.organizationId === organization.id);
        return `<section class="org-group" aria-labelledby="organization-heading-${escape(organization.id)}"><label class="org-choice"><input type="checkbox" data-org-choice="${escape(organization.id)}"><span id="organization-heading-${escape(organization.id)}">${escape(organization.name)}</span><small>${escape(cabinetCount(group.length))}</small></label><div class="org-cabinets">${group.map(cabinet => `<label class="org-cabinet"><input type="checkbox" data-org-cabinet="${escape(cabinet.id)}"><span>${escape(cabinet.label)}</span></label>`).join('')}</div></section>`;
      }).join('')}
      <p id="organization-selection-summary" class="org-selection-summary" role="status" aria-live="polite"></p><p id="organization-selection-mode" class="hint"></p></div>
      <div class="drawer-foot"><button type="button" class="btn" data-org-action="close">Отмена</button><button type="button" class="btn primary" data-org-action="apply">Применить</button></div>`;
    syncPending();
  }
  function open() {
    if (dialog?.open) return;
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'organization-dialog';
      dialog.className = 'modal org-dialog';
      dialog.setAttribute('aria-labelledby', 'organization-dialog-title');
      document.body.appendChild(dialog);
      dialog.addEventListener('close', () => { pending = []; renderHeader(); focus(); });
      dialog.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        if (button.dataset.orgAction === 'close') close();
        else if (button.dataset.orgAction === 'apply') apply(pending);
        else if (button.dataset.orgMarketplace) {
          pending = allowed().filter(cabinet => button.dataset.orgMarketplace === 'all' || cabinet.marketplace === button.dataset.orgMarketplace).map(cabinet => cabinet.id);
          syncPending();
        }
      });
      dialog.addEventListener('change', event => {
        const input = event.target;
        if (!input.matches('input[type="checkbox"]')) return;
        const ids = input.dataset.orgCabinet ? [input.dataset.orgCabinet]
          : allowed().filter(cabinet => cabinet.organizationId === input.dataset.orgChoice).map(cabinet => cabinet.id);
        const chosen = new Set(pending);
        ids.forEach(id => input.checked ? chosen.add(id) : chosen.delete(id));
        pending = normalize([...chosen]);
        syncPending();
      });
    }
    pending = selection();
    renderDialog();
    dialog.showModal();
    renderHeader();
  }
  function setProfile(nextProfile) {
    close();
    profile = nextProfile === 'manager' ? 'manager' : 'owner';
    load();
    renderHeader();
  }
  function init(options = {}) {
    onChange = typeof options.onChange === 'function' ? options.onChange : null;
    ensureCatalog();
    setProfile(options.profile);
    return root.OrganizationScope;
  }

  root.OrganizationScope = { organizations, cabinets, init, setProfile, selection, selectedOrganizations,
    singleOrganization, isCombined, contextKey, scopedRows, catalogFor, allRows, label, describe,
    open, focus, organizationName, chooseOrganization };
})(window);
