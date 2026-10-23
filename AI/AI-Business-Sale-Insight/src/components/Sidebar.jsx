import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  const tabs = [
    { name: 'Dashboard', path: '/' },
    { name: 'Analytics', path: '/analytics' },
  ];

  return (
    <>
      {/* Mobile toggle button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 bg-slate-800 text-white p-2 rounded"
        onClick={toggleSidebar}
      >
        ☰
      </button>

      {/* Sidebar */}
      <div
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-slate-800 text-white transform ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 transition-transform duration-300 ease-in-out`}
      >
        <div className="p-4">
          <h2 className="text-lg font-bold mb-4">Menu</h2>
          <ul>
            {tabs.map((tab) => (
              <li key={tab.path} className="mb-2">
                <Link
                  to={tab.path}
                  className={`block p-2 rounded hover:bg-slate-700 transition-colors ${
                    location.pathname === tab.path ? 'bg-blue-500' : ''
                  }`}
                  onClick={() => setIsOpen(false)} // Close on mobile after click
                >
                  {tab.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={toggleSidebar}
        ></div>
      )}
    </>
  );
};

export default Sidebar;