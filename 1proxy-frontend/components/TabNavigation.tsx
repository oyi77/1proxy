"use client";

import { useTheme } from "@/app/theme-provider";

interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  const { theme } = useTheme();
  const tabs = [
    { id: "home", label: "Home" },
    { id: "list", label: "Proxy List" },
    { id: "rotation", label: "Proxy Rotation" },
  ];

  const getTabStyle = (tabId: string) => ({
    backgroundColor: activeTab === tabId ? 'var(--retro-pink)' : 'transparent',
    color: activeTab === tabId ? '#000000' : (theme === 'dark' ? 'var(--dark-text)' : '#6B7280'),
    border: activeTab === tabId ? '3px solid #000000' : '3px solid transparent'
  });

  return (
    <div className="flex border-b-4 gap-4 mb-6" style={{ borderColor: '#000000' }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className="px-6 py-3 font-bold transition-all relative"
          style={{
            ...getTabStyle(tab.id),
            fontFamily: "'Bangers', cursive",
            fontSize: '1.125rem',
            textTransform: 'uppercase'
          }}
        >
          {tab.label}
          {activeTab === tab.id && (
            <div className="absolute bottom-0 left-0 right-0 h-1" style={{ backgroundColor: '#000000' }} />
          )}
        </button>
      ))}
    </div>
  );
}
