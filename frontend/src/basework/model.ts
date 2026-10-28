export const applications = [
  { id: 'marketplace', title: 'Marketplace', description: 'Кабинеты и аналитика маркетплейсов.', keywords: 'товары продажи кабинеты' },
  { id: 'reports', title: 'WB-отчёты', description: 'Подготовка и выгрузка отчётов Wildberries.', keywords: 'wb wildberries отчеты выгрузка' },
  { id: 'sources', title: 'Источники данных', description: 'Покрытие, свежесть и ошибки загрузок.', keywords: 'загрузки данные источники' },
  { id: 'airflow', title: 'Airflow', description: 'Просмотр процессов, запусков и журналов.', keywords: 'процессы запуски задачи журналы' },
  { id: 'bloggers', title: 'Блогеры', description: 'Размещения и результаты замеров просмотров.', keywords: 'просмотры размещения блогеры' },
  { id: 'faq', title: 'Справочник', description: 'Вопросы команды и контакты ответственных.', keywords: 'faq вопросы контакты справочник' },
  { id: 'rooms', title: 'Переговорки', description: 'Расписание и бронирование переговорных.', keywords: 'комнаты встречи расписание переговорки' },
] as const;

export type Application = typeof applications[number];
export type ApplicationId = Application['id'];
export type Entitlement = {
  id: ApplicationId;
  access: 'allowed' | 'denied';
  availability: 'available' | 'unavailable';
};
export type Bootstrap = {
  session: { status: 'authenticated'; user: { id: string; displayName: string } };
  applications: Entitlement[];
};
export type SessionStatus = 'anonymous' | 'expired' | 'mfa_required';
export type Resource =
  | { status: 'loading' | 'error' | 'unavailable' | 'forbidden' | SessionStatus }
  | { status: 'ready'; data: Bootstrap };
export type DirectoryEntry = Application & { access: 'allowed' | 'unknown'; availability: Entitlement['availability'] };
export type Route = { kind: 'home' | 'profile' | 'notifications' | 'missing' } | { kind: 'application'; application: Application };

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isApplicationId(value: unknown): value is ApplicationId {
  return applications.some(application => application.id === value);
}

export function parseBootstrap(value: unknown): Resource {
  if (!isObject(value) || !isObject(value.session)) return { status: 'error' };
  const session = value.session;
  if (session.status === 'anonymous' || session.status === 'expired' || session.status === 'mfa_required') {
    return { status: session.status };
  }
  if (session.status !== 'authenticated' || !isObject(session.user)) return { status: 'error' };
  const { id, displayName } = session.user;
  if (typeof id !== 'string' || !id.trim() || id.length > 200 || typeof displayName !== 'string' || !displayName.trim() || displayName.length > 500) {
    return { status: 'error' };
  }
  if (!Array.isArray(value.applications)) return { status: 'error' };
  const entitlements: Entitlement[] = [];
  const seen = new Set<ApplicationId>();
  for (const item of value.applications) {
    if (!isObject(item) || typeof item.id !== 'string') return { status: 'error' };
    // Неизвестные разделы не расширяют разрешённый состав BaseWork.
    if (!isApplicationId(item.id)) continue;
    if (seen.has(item.id) || (item.access !== 'allowed' && item.access !== 'denied') ||
        (item.availability !== 'available' && item.availability !== 'unavailable')) return { status: 'error' };
    seen.add(item.id);
    entitlements.push({ id: item.id, access: item.access, availability: item.availability });
  }
  return {
    status: 'ready',
    data: { session: { status: 'authenticated', user: { id, displayName } }, applications: entitlements },
  };
}

export function directory(resource: Resource): DirectoryEntry[] {
  if (resource.status === 'unavailable' || resource.status === 'error') {
    return applications.map(application => ({ ...application, access: 'unknown', availability: 'unavailable' }));
  }
  if (resource.status !== 'ready') return [];
  return applications.flatMap(application => {
    const entitlement = resource.data.applications.find(item => item.id === application.id && item.access === 'allowed');
    return entitlement ? [{ ...application, access: 'allowed' as const, availability: entitlement.availability }] : [];
  });
}

function normalise(value: string) {
  return value.toLocaleLowerCase('ru-RU').replaceAll('ё', 'е').trim();
}

export function searchApplications(entries: DirectoryEntry[], query: string) {
  const words = normalise(query).split(/\s+/).filter(Boolean);
  return entries.filter(entry => {
    const text = normalise(`${entry.title} ${entry.description} ${entry.keywords}`);
    return words.every(word => text.includes(word));
  });
}

export const applicationPath = (id: ApplicationId) => `/basework/apps/${id}`;

export function resolveRoute(pathname: string): Route {
  const path = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname;
  if (path === '/' || path === '/basework') return { kind: 'home' };
  if (path === '/basework/profile') return { kind: 'profile' };
  if (path === '/basework/notifications') return { kind: 'notifications' };
  const application = applications.find(item => applicationPath(item.id) === path);
  return application ? { kind: 'application', application } : { kind: 'missing' };
}

export type PanelKind = 'loading' | 'error' | 'unavailable' | 'forbidden' | 'anonymous' | 'expired' | 'mfa_required' | 'not_connected' | 'empty' | 'missing' | 'module_unavailable' | 'module_error';
export const panels: Record<PanelKind, { title: string; description: string }> = {
  loading: { title: 'Проверяем доступ…', description: 'Ожидаем ответ о сессии и доступных приложениях.' },
  error: { title: 'Не удалось проверить доступ', description: 'Ответ сервиса не удалось обработать. Повторите проверку.' },
  unavailable: { title: 'Сервис доступа недоступен', description: 'Подключение ещё не настроено или сервис временно не отвечает. Доступ к приложениям не подтверждён.' },
  forbidden: { title: 'Нет доступа', description: 'Для этого раздела нет подтверждённого разрешения. Уточните доступ у администратора приложения.' },
  anonymous: { title: 'Вы не вошли в систему', description: 'Войдите по логину и паролю, чтобы открыть свои приложения.' },
  expired: { title: 'Сессия завершена', description: 'Войдите снова по логину и паролю.' },
  mfa_required: { title: 'Нужно подтверждение входа', description: 'Сервис требует дополнительную проверку. Доступ к приложениям закрыт до её завершения.' },
  module_unavailable: { title: 'Модуль недоступен', description: 'Раздел временно не отвечает. Повторите проверку позже или выберите другое приложение.' },
  module_error: { title: 'Ошибка раздела', description: 'Этот раздел не удалось отобразить. Повторите открытие или перейдите в другое приложение.' },
  not_connected: { title: 'Раздел ещё не подключён', description: 'Оболочка готова к подключению модуля. Рабочие данные и действия появятся на следующем этапе.' },
  empty: { title: 'Нет доступных приложений', description: 'Для текущей сессии сервис не вернул разрешённых приложений. Уточните назначения доступа.' },
  missing: { title: 'Страница не найдена', description: 'Проверьте адрес или вернитесь на рабочий стол.' },
};

export function applicationPanel(resource: Resource, id: ApplicationId): PanelKind {
  if (resource.status !== 'ready') return resource.status;
  const entitlement = resource.data.applications.find(item => item.id === id);
  if (!entitlement || entitlement.access !== 'allowed') return 'forbidden';
  return entitlement.availability === 'unavailable' ? 'module_unavailable' : 'not_connected';
}

export async function requestBootstrap(signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<Resource> {
  const response = await fetcher('/api/v1/basework/bootstrap', {
    credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    headers: { Accept: 'application/json' }, signal,
  });
  if (response.status === 401) {
    try {
      const value: unknown = await response.json();
      return { status: isObject(value) && value.status === 'session_expired' ? 'expired' : 'anonymous' };
    } catch { return { status: 'anonymous' }; }
  }
  if (response.status === 403) {
    try {
      const value: unknown = await response.json();
      return { status: isObject(value) && value.status === 'mfa_required' ? 'mfa_required' : 'forbidden' };
    } catch { return { status: 'forbidden' }; }
  }
  if ([404, 502, 503, 504].includes(response.status)) return { status: 'unavailable' };
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return { status: 'error' };
  try { return parseBootstrap(await response.json()); }
  catch { return { status: 'error' }; }
}
