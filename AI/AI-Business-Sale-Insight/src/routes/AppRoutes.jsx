import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from '../components/Layout';
import Dashboard from '../pages/Dashboard';
import Analytics from '../pages/Analytics';

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
