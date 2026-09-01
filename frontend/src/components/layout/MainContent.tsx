import { Outlet } from 'react-router-dom'

export function MainContent() {
  return (
    <main className="main-content" id="main-content">
      <Outlet />
    </main>
  )
}
