import './theme-v1.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BaseWork } from './basework/BaseWork';
import './basework/workspace.css';

createRoot(document.getElementById('root')!).render(<StrictMode><BaseWork /></StrictMode>);
