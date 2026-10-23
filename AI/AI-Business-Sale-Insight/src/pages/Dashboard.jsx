import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer } from 'recharts';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const SERVER = import.meta.env.VITE_SERVER_URL || 'http://localhost:5000';

const Dashboard = () => {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: '', signup_date: new Date().toISOString().split('T')[0], gender: '', region: '', loyalty_tier: '' });
  const [result, setResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [mappings, setMappings] = useState({});
  const [productPredictions, setProductPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trainOpen, setTrainOpen] = useState(false);
  const [epochs, setEpochs] = useState(10);
  const [fetchingData, setFetchingData] = useState(true);

  useEffect(() => {
    setFetchingData(true);
    Promise.all([
      fetch(`${SERVER}/analyze`).then(r => r.json()),
      fetch(`${SERVER}/mappings`).then(r => r.json()),
      fetch(`${SERVER}/product-prediction`).then(r => r.json())
    ]).then(([d, m, p]) => {
      setAnalytics(d);
      setMappings(m);
      setProductPredictions(Array.isArray(p) ? p : []);
    }).catch(console.error).finally(() => setFetchingData(false));
  }, []);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${SERVER}/add-customer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        toast.success("Product prediction completed successfully!");
        setOpen(false);
        // Refresh analytics after adding
        Promise.all([
          fetch(`${SERVER}/analyze`).then(r => r.json()),
          fetch(`${SERVER}/mappings`).then(r => r.json())
        ]).then(([d, m]) => {
          setAnalytics(d);
          setMappings(m);
        }).catch(console.error);
      } else {
        toast.error("Failed to predict product. Please try again.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error predicting product. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${SERVER}/retrain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ epochs: parseInt(epochs) })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Training complete! Accuracy: ${data.validation_accuracy}%`);
        setTrainOpen(false);
        // Refresh analytics to show updated data from CSV
        const [d, m] = await Promise.all([
          fetch(`${SERVER}/analyze`).then(r => r.json()),
          fetch(`${SERVER}/mappings`).then(r => r.json())
        ]);
        setAnalytics(d);
        setMappings(m);
      } else {
        toast.error("Training failed.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error connecting to server.");
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data
  const regionData = analytics ? Object.entries(
    Object.entries(analytics.sales_by_region || {}).reduce((acc, [k, v]) => {
      const region = mappings.region?.[k] || k;
      acc[region] = (acc[region] || 0) + v;
      return acc;
    }, {})
  ).map(([region, sales]) => ({ region, sales })) : [];
  const loyaltyData = analytics ? Object.entries(analytics.segment_distribution || {}).map(([k, v]) => ({ segment: mappings.segment?.[k] || `Segment ${k}`, count: v })) : [];

  // New data for distributions
  const genderData = analytics ? Object.entries(
    Object.entries(analytics.gender_counts || {}).reduce((acc, [k, v]) => {
      const gender = mappings.gender?.[k] || k;
      acc[gender] = (acc[gender] || 0) + v;
      return acc;
    }, {})
  ).map(([gender, count]) => ({ gender, count })).filter(item => item.count > 0) : [];
  const regionCountData = analytics ? Object.entries(
    Object.entries(analytics.region_counts || {}).reduce((acc, [k, v]) => {
      const region = mappings.region?.[k] || k;
      acc[region] = (acc[region] || 0) + v;
      return acc;
    }, {})
  ).map(([region, count]) => ({ region, count })) : [];
  const loyaltyCountData = analytics ? Object.entries(analytics.loyalty_counts || {}).map(([k, v]) => ({ tier: mappings.loyalty_tier?.[k] || k, count: v })) : [];

  // Loyalty tier counts data
  const loyaltyTierData = analytics ? Object.entries(analytics.loyalty_counts || {}).reduce((acc, [k, v]) => {
    const tier = mappings.loyalty_tier?.[k] || k;
    acc[tier] = (acc[tier] || 0) + v;
    return acc;
  }, {}) : {};
  const loyaltyTierDataArray = Object.entries(loyaltyTierData).map(([tier, count]) => ({ tier, count }));
  const maxSellingTier = loyaltyTierDataArray.length > 0 ? loyaltyTierDataArray.reduce((max, t) => t.count > max.count ? t : max) : null;
  const minSellingTier = loyaltyTierDataArray.length > 0 ? loyaltyTierDataArray.reduce((min, t) => t.count < min.count ? t : min) : null;

  // Product prediction data
  const predictionData = productPredictions.map(p => ({ name: p.name, change: p.prediction }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex gap-4">
          <button onClick={() => setTrainOpen(true)} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
            Train Model
          </button>
          <button onClick={() => setOpen(true)} className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
            Add Form
          </button>
        </div>
      </div>


      {result && (
        <div className="bg-slate-800 p-4 rounded mb-4">
          <p><strong>Customer ID:</strong> {result.customer_id}</p>
          <p><strong>Prediction:</strong> {JSON.stringify(result.prediction)}</p>
          <p><strong>Validation Accuracy:</strong> {result.validation_accuracy}</p>
        </div>
      )}

      <div className="mb-6">
        <h3 className="font-semibold mb-2">Model Accuracy Plot</h3>
        <div className="bg-white p-2 rounded">
          <img src={`${SERVER}/accuracy-plot`} alt="accuracy" className="w-full h-96 object-contain" />
        </div>
      </div>

      {fetchingData ? (
        <div className="flex flex-col items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-gray-400">Loading analytics data...</p>
        </div>
      ) : (
        analytics && (
        <>
          <div className="mb-6 flex space-x-6">
            <div className="flex-1">
              <h3 className="font-semibold mb-2">Regional Sales Distribution</h3>
              <BarChart width={350} height={300} data={regionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="region" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="sales" fill="#8884d8" />
              </BarChart>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-2">Customer Gender Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={genderData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ gender, percent }) => `${gender} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {genderData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mb-6 flex space-x-6">
            <div className="flex-1">
              <h3 className="font-semibold mb-2">Customer Region Distribution</h3>
              <LineChart width={350} height={300} data={regionCountData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="region" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="count" stroke="#82ca9d" />
              </LineChart>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-2">Loyalty Tier Distribution</h3>
              <BarChart width={350} height={300} data={loyaltyTierDataArray}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tier" angle={-45} textAnchor="end" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
              <div className="mt-4">
                <p>Maximum Selling Tier: {maxSellingTier ? `${maxSellingTier.tier} (${maxSellingTier.count} customers)` : 'No data'}</p>
                <p>Lower Selling Tier: {minSellingTier ? `${minSellingTier.tier} (${minSellingTier.count} customers)` : 'No data'}</p>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-semibold mb-2">Loyalty Tier Sales Prediction</h3>
            <BarChart width={600} height={300} data={predictionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" />
              <YAxis />
              <Tooltip formatter={(value) => [`${value}%`, 'Predicted Change']} />
              <Legend />
              <Bar dataKey="change">
                {predictionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.change >= 0 ? "#82ca9d" : "#ff7c7c"} />
                ))}
              </Bar>
            </BarChart>
          </div>
        </>
        )
      )}

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white text-black rounded-lg shadow-2xl w-11/12 max-w-md p-6 transform transition-all duration-300 scale-100">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-800">Add New Customer</h3>
              <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input name="email" placeholder="Enter email" onChange={handleChange} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Signup Date</label>
                <input name="signup_date" value={form.signup_date} disabled className="w-full p-3 border border-gray-300 rounded-lg bg-gray-100 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                <div className="flex gap-6">
                  <label className="flex items-center">
                    <input type="radio" name="gender" value="male" onChange={handleChange} className="mr-2" required />
                    <span className="text-gray-700">Male</span>
                  </label>
                  <label className="flex items-center">
                    <input type="radio" name="gender" value="female" onChange={handleChange} className="mr-2" />
                    <span className="text-gray-700">Female</span>
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
                <input name="region" placeholder="Enter region" onChange={handleChange} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Loyalty Tier</label>
                <select name="loyalty_tier" onChange={handleChange} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" required>
                  <option value="">Select Loyalty Tier</option>
                  {mappings.loyalty_tier && Object.values(mappings.loyalty_tier).map(tier => (
                    <option key={tier} value={tier}>{tier.charAt(0).toUpperCase() + tier.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setOpen(false)} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
                <button type="submit" disabled={loading} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors cursor-pointer disabled:opacity-50">
                  {loading ? 'Adding...' : 'Submit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Train Modal */}
      {trainOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white text-black rounded-lg shadow-2xl w-11/12 max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-800">Train Model</h3>
              <button onClick={() => setTrainOpen(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <form onSubmit={handleTrain} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Epochs</label>
                <input type="number" value={epochs} onChange={(e) => setEpochs(e.target.value)} className="w-full p-3 border border-gray-300 rounded-lg" min="1" required />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setTrainOpen(false)} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={loading} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                  {loading ? 'Training...' : 'Start Training'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
};

export default Dashboard;