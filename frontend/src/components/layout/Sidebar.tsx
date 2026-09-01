import { NavLink } from 'react-router-dom'

import { env } from '../../config/env'

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand" aria-label="Gestor de Compras">
        <span>Gestor</span>
        <strong>de Compras</strong>
      </div>

      <nav className="sidebar-nav" aria-label="Navegação principal">
        <p className="nav-section-label">Navegação</p>
        <NavLink
          className={({ isActive }) =>
            `nav-item${isActive ? ' nav-item-active' : ''}`
          }
          to="/"
          end
        >
          Início
        </NavLink>

        <NavLink
          className={({ isActive }) =>
            `nav-item${isActive ? ' nav-item-active' : ''}`
          }
          to="/gestor"
        >
          Gestor de Compras
        </NavLink>

        <NavLink
          className={({ isActive }) =>
            `nav-item${isActive ? ' nav-item-active' : ''}`
          }
          to="/dashboard"
        >
          Dashboard
        </NavLink>

        <p className="nav-section-label nav-section-future">Em breve</p>
        <span className="nav-item nav-item-disabled" aria-disabled="true">
          Relatórios
        </span>
      </nav>

      <div className="sidebar-footer">
        <span>{env.appName}</span>
        <small>v{env.appVersion}</small>
      </div>
    </aside>
  )
}
