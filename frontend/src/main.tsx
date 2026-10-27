import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BaseWork } from './basework/BaseWork';

createRoot(document.getElementById('root')!).render(<StrictMode><BaseWork /></StrictMode>);
