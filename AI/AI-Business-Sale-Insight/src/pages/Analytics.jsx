import React, { useEffect, useState } from 'react';

const SERVER = import.meta.env.VITE_SERVER_URL || 'http://localhost:5000';

const Analytics = () => {
  const [data, setData] = useState(null);
  const [mappings, setMappings] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [loyaltyFilter, setLoyaltyFilter] = useState('');
  const [genderFilter, setGenderFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const params = new URLSearchParams({
      page: currentPage,
      limit: 10,
      loyalty_filter: loyaltyFilter,
      gender_filter: genderFilter,
      from_date: fromDate,
      to_date: toDate,
      search: search
    });
    Promise.all([
      fetch(`${SERVER}/analyze?${params}`).then(r => r.json()),
      fetch(`${SERVER}/mappings`).then(r => r.json())
    ]).then(([d, m]) => {
      setData(d);
      setMappings(m);
    }).catch(console.error);
  }, [currentPage, loyaltyFilter, genderFilter, fromDate, toDate, search]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [loyaltyFilter, genderFilter, fromDate, toDate, search]);

  if (!data || !mappings) return <div className="p-6">Loading analytics...</div>;

  // Decode the table data (removed, as table is removed)
  // const decodedTable = (data.loyalty_region_gender || []).map(row => ({
  //   region: mappings.region?.[row.region] || row.region,
  //   loyalty_tier: mappings.loyalty_tier?.[row.loyalty_tier] || row.loyalty_tier,
  //   gender: mappings.gender?.[row.gender] || row.gender,
  //   purchase_amount: row.purchase_amount
  // }));

  // Customers table data
  const customers = data.sample_customers || [];
  const decodedCustomers = customers.map(c => ({
    ...c,
    gender: mappings.gender?.[c.gender] || c.gender,
    region: mappings.region?.[c.region] || c.region,
    loyalty_tier: mappings.loyalty_tier?.[c.loyalty_tier] || c.loyalty_tier
  }));

  // Pagination from server
  const totalPages = data.total_customers ? Math.ceil(data.total_customers / 10) : 1;

  // Aggregate sales by region to avoid duplicates
  const aggregatedSales = data.sales_by_region ? Object.entries(data.sales_by_region).reduce((acc, [k, v]) => {
    const region = mappings.region?.[k] || k;
    acc[region] = (acc[region] || 0) + v;
    return acc;
  }, {}) : {};

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Analytics</h2>

      <div className="mb-4">
        <h3 className="font-semibold">Regional Sales Overview</h3>
        <ul className="list-disc ml-6">
          {Object.entries(aggregatedSales).map(([r, v]) => (
            <li key={r}>{r}: {v}</li>
          ))}
        </ul>
      </div>

      <div className="mb-4">
        <h3 className="font-semibold">Customer Data Table</h3>
        <div className="mb-4 flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="Search by ID or Email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="p-2 border border-gray-600 rounded bg-slate-800 text-white"
          />
          <select value={loyaltyFilter} onChange={(e) => setLoyaltyFilter(e.target.value)} className="p-2 border border-gray-600 rounded bg-slate-800 text-white">
            <option value="">All Loyalty Tiers</option>
            {Object.values(mappings.loyalty_tier || {}).map(tier => (
              <option key={tier} value={tier}>{tier}</option>
            ))}
          </select>
          <select value={genderFilter} onChange={(e) => setGenderFilter(e.target.value)} className="p-2 border border-gray-600 rounded bg-slate-800 text-white">
            <option value="">All Genders</option>
            {Object.values(mappings.gender || {}).map(gen => (
              <option key={gen} value={gen}>{gen}</option>
            ))}
          </select>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="p-2 border border-gray-600 rounded bg-slate-800 text-white"
            placeholder="From Date"
          />
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="p-2 border border-gray-600 rounded bg-slate-800 text-white"
            placeholder="To Date"
          />
        </div>
        <table className="w-full text-left bg-slate-800 p-2 rounded">
          <thead>
            <tr>
              <th className="p-2">Customer ID</th>
              <th className="p-2">Email</th>
              <th className="p-2">Signup Date</th>
              <th className="p-2">Gender</th>
              <th className="p-2">Region</th>
              <th className="p-2">Loyalty Tier</th>
              <th className="p-2">Segment</th>
            </tr>
          </thead>
          <tbody>
            {decodedCustomers.map((c, idx) => (
              <tr key={idx} className="border-t">
                <td className="p-2">{c.customer_id}</td>
                <td className="p-2">{c.email}</td>
                <td className="p-2">{c.signup_date}</td>
                <td className="p-2">{c.gender}</td>
                <td className="p-2">{c.region}</td>
                <td className="p-2">{c.loyalty_tier}</td>
                <td className="p-2">{c.customer_segment}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 flex justify-between">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="p-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span>Page {currentPage} of {totalPages}</span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="p-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

    </div>
  );
};

export default Analytics;