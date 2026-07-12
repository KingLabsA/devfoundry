export type Page = "forge" | "runs" | "services" | "settings";

const ITEMS: { id: Page; icon: string; label: string }[] = [
  { id: "forge", icon: "⚒", label: "Forge" },
  { id: "runs", icon: "🗂", label: "Runs" },
  { id: "services", icon: "🐳", label: "Services" },
  { id: "settings", icon: "⚙", label: "Settings" },
];

export function Sidebar({ page, onNavigate, servicesUp }: {
  page: Page;
  onNavigate: (p: Page) => void;
  servicesUp: boolean;
}) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand" title="DevFoundry">⬢</div>
      {ITEMS.map((item) => (
        <button
          key={item.id}
          className={page === item.id ? "nav-item active" : "nav-item"}
          onClick={() => onNavigate(item.id)}
          title={item.label}
        >
          <span className="nav-icon">{item.icon}</span>
          <span className="nav-label">{item.label}</span>
          {item.id === "services" && (
            <span className={`dot ${servicesUp ? "up" : "down"}`} style={{ marginLeft: "auto" }} />
          )}
        </button>
      ))}
    </nav>
  );
}
