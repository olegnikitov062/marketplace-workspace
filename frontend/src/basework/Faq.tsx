import { useEffect, useRef, useState } from 'react';
import { requestFaq, type FaqResource } from './faqApi';
import { Link } from './navigation';

const messages = {
  loading: ['Загружаем справочник…', 'Получаем вопросы и контакты.'],
  unavailable: ['Источник справочника недоступен', 'Не удалось получить данные. Попробуйте обновить справочник позже.'],
  error: ['Не удалось прочитать справочник', 'Источник вернул некорректный ответ. Повторите загрузку позже.'],
  forbidden: ['Нет доступа', 'Для справочника нет действующего разрешения. Уточните доступ у администратора.'],
  expired: ['Сессия завершена', 'Войдите снова по логину и паролю.'],
  mfa_required: ['Нужно подтверждение входа', 'Завершите проверку аккаунта перед открытием справочника.'],
} as const;

export function Faq() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [revision, setRevision] = useState(0);
  const [resource, setResource] = useState<FaqResource>({ status: 'loading' });
  const [selectedId, setSelectedId] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const generation = useRef(0);
  const change = (action: () => void) => {
    generation.current += 1;
    setResource({ status: 'loading' }); setSelectedId(''); action();
  };
  useEffect(() => {
    const current = generation.current;
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => {
      active = false;
      controller.abort();
      if (current === generation.current) setResource({ status: 'unavailable' });
    }, 8000);
    const debounce = window.setTimeout(() => {
      requestFaq(query, category, controller.signal).then(result => {
        if (active && current === generation.current) {
          setResource(result);
          setCategories(result.status === 'ready' ? result.data.categories : []);
        }
      }).catch(() => { if (active && current === generation.current) setResource({ status: 'unavailable' }); })
        .finally(() => window.clearTimeout(timeout));
    }, 200);
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); window.clearTimeout(debounce); };
  }, [query, category, revision]);
  const data = resource.status === 'ready' ? resource.data : null;
  const selected = data?.items.find(item => item.id === selectedId) ?? data?.items[0];
  const normalize = (value: string) => value.toLocaleLowerCase('ru').replaceAll('ё', 'е');
  const words = normalize(query).split(/\s+/).filter(Boolean);
  const people = data?.people.filter(person => words.every(word => normalize(`${person.name} ${person.role}`).includes(word))) ?? [];
  return <div className="bw-columns bw-faq-columns">
    <section className="bw-surface bw-section bw-faq-main" aria-label="Вопросы команды">
      <form className="bw-faq-filters" role="search" onSubmit={event => { event.preventDefault(); change(() => setRevision(value => value + 1)); }}>
        <label>Поиск по вопросам и контактам<input type="search" name="faq-search" autoComplete="off" maxLength={300}
          placeholder="Вопрос, имя или должность" value={query} onChange={event => change(() => setQuery(event.target.value))} /></label>
        <label>Категория<select value={category} onChange={event => change(() => setCategory(event.target.value))}>
          <option value="">Все категории</option>
          {(data?.categories ?? (resource.status === 'loading' ? categories : [])).map(cat => <option key={cat} value={cat}>{cat}</option>)}
        </select></label>
        <button type="submit" className="bw-button">Обновить</button>
      </form>
      {resource.status !== 'ready' ? <div className="bw-state" role={resource.status === 'loading' ? 'status' : 'alert'} aria-busy={resource.status === 'loading'}>
        <h2>{messages[resource.status][0]}</h2><p>{messages[resource.status][1]}</p>
        {resource.status === 'expired' ? <a href="/auth/basework/login" className="bw-button">Войти</a> : null}
        {resource.status === 'mfa_required' ? <a href="/auth/mfa/setup/">Подтвердить вход</a> : null}
      </div> : <>
        <p className="bw-muted bw-faq-count" role="status">Найдено вопросов: {resource.data.items.length} из {resource.data.total}</p>
        {resource.data.items.length ? <ul className="bw-faq-list">{resource.data.items.map(item => <li key={item.id}>
          <button type="button" aria-pressed={selected?.id === item.id} onClick={() => setSelectedId(item.id)}>
            <span className="bw-muted">{item.cat}</span><strong>{item.q}</strong>
            <span>{item.contacts.length ? item.contacts.map(([name]) => name).join(', ') : 'Ответственные не указаны'}</span>
          </button>
        </li>)}</ul> : <div className="bw-state"><h2>{query || category ? 'Ничего не найдено' : 'Вопросов пока нет'}</h2>
          <p>{query || category ? 'Измените запрос или выберите другую категорию.' : 'В источнике справочника нет вопросов.'}</p></div>}
        <p className="bw-muted bw-faq-version">Версия {resource.data.version}{resource.data.updatedAt ? ` · Обновлено: ${resource.data.updatedAt}` : ''}</p>
      </>}
      <div className="bw-section-footer"><Link href="/basework/">На рабочий стол</Link></div>
    </section>
    <aside className="bw-aside bw-faq-details" aria-label="Ответственные и команда">
      {selected && data ? <section aria-live="polite"><p className="bw-muted">{selected.cat}</p><h2>{selected.q}</h2>
        <h3>К кому обратиться</h3>
        {selected.contacts.length ? <ul className="bw-faq-contacts">{selected.contacts.map(([name, note], index) => <li key={`${name}-${index}`}>
          <strong>{name}</strong><p>{data.people.find(person => person.name === name)?.role}</p>{note ? <p className="bw-faq-note">{note}</p> : null}
        </li>)}</ul> : <p>Ответственные не указаны.</p>}
      </section> : <section><h2>К кому обратиться</h2><p>Выберите вопрос, чтобы увидеть ответственных и примечания.</p></section>}
      {data ? <section><details open={Boolean(query)}><summary>Команда: {people.length}</summary>
        {people.length ? <ul className="bw-faq-contacts">{people.map(person => <li key={person.name}><strong>{person.name}</strong><p>{person.role}</p></li>)}</ul> : <p>Контакты не найдены.</p>}
      </details></section> : null}
    </aside>
  </div>;
}
