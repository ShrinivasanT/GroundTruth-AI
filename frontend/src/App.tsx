import { BrowserRouter, Routes, Route } from 'react-router-dom';
import * as Tooltip from '@radix-ui/react-tooltip';
import { AppLayout } from './components/layout/AppLayout';
import { WorkspacePage } from './pages/WorkspacePage';
import { AccountSettingsPage } from './pages/AccountSettingsPage';

export default function App() {
  return (
    <Tooltip.Provider delayDuration={300}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<WorkspacePage />} />
            <Route path="account" element={<AccountSettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </Tooltip.Provider>
  );
}
