import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const Layout = () => {
  return (
    <div className="flex min-h-screen bg-slate-900 text-white">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default Layout;