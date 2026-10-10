import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import { Search, Clock, Info } from 'lucide-react';
import { VerifyPage } from './pages/VerifyPage';
import { ReportPage } from './pages/ReportPage';
import { HistoryPage } from './pages/HistoryPage';
import { AboutPage } from './pages/AboutPage';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* ── Header ────────────────────────────────────── */}
        <header className="app-header">
          <div className="header-inner">
            <Link to="/" className="logo-section">
              <div className="logo-icon">
                <Search size={20} />
              </div>
              <div className="logo-text">
                Truth<span>Lens</span> AI
              </div>
            </Link>

            <nav className="nav-links">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Search size={16} /> Verify
              </NavLink>
              <NavLink
                to="/history"
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Clock size={16} /> History
              </NavLink>
              <NavLink
                to="/about"
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Info size={16} /> About
              </NavLink>
            </nav>
          </div>
        </header>

        {/* ── Main ──────────────────────────────────────── */}
        <main className="app-main">
          <Routes>
            <Route path="/" element={<VerifyPage />} />
            <Route path="/report/:id" element={<ReportPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </main>

        {/* ── Footer ────────────────────────────────────── */}
        <footer className="app-footer">
          TruthLens AI — Evidence-grounded claim verification.
          Results should be independently verified.
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
