const NAV_ITEMS = [
  { label: '会话', active: true },
  { label: '分析', active: false },
]

export function SidebarNav() {
  return (
    <nav className="sidebar-nav" aria-label="主导航">
      <div className="sidebar-nav__brand">
        <span className="sidebar-nav__brand-mark">如</span>
      </div>
      <div className="sidebar-nav__items">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`sidebar-nav__item${item.active ? ' sidebar-nav__item--active' : ''}`}
            aria-current={item.active ? 'page' : undefined}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="sidebar-nav__footer">
        <button type="button" className="sidebar-nav__item sidebar-nav__item--footer">
          设置
        </button>
      </div>
    </nav>
  )
}
