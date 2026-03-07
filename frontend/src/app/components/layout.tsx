import { Outlet, useNavigate, useLocation } from "react-router";
import { Eye, Upload, BarChart3 } from "lucide-react";

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Upload", icon: Upload },
    { path: "/history", label: "Reports", icon: BarChart3 },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-200" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-to-b from-blue-500/[0.04] via-purple-500/[0.02] to-transparent rounded-full blur-3xl" />
      </div>

      {/* Navbar */}
      <nav className="relative z-10 border-b border-white/[0.06] bg-[#0a0a0f]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
          >
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500">
              <Eye className="w-4 h-4 text-white" />
            </div>
            <span className="text-white tracking-tight" style={{ fontWeight: 700 }}>
              VisionScore
            </span>
          </button>

          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const active =
                item.path === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(item.path);
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                    active
                      ? "bg-white/[0.08] text-white"
                      : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.04]"
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10">
        <Outlet />
      </main>
    </div>
  );
}