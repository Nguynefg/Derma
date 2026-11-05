import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import '@fontsource/be-vietnam-pro/400.css';
import '@fontsource/be-vietnam-pro/500.css';
import '@fontsource/be-vietnam-pro/600.css';
import '@fontsource/be-vietnam-pro/700.css';
import '@fontsource/be-vietnam-pro/800.css';
import '../shared/styles/site.css';
import '../features/assistant/assistant.css';
import '../shared/styles/refinement.css';
import '../shared/styles/botanical.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
