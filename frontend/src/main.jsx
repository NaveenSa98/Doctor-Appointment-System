import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';
import './styles/forms.css';
import './styles/extras.css';
import './styles/signin.css';
import './styles/account.css';
import './styles/admin.css';
import './styles/schedule.css';
import './styles/polish.css';
import './styles/search.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
