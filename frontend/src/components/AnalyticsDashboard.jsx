/**
 * Analytics Dashboard Component
 *
 * Real-time analytics panel for content creators.
 * Polls the /api/analytics/ endpoint every 30 seconds for fresh data.
 * Displays watch time, retention curves, geographic breakdown, and device stats.
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatDuration, formatNumber } from '../utils/format';
import RetentionChart from './charts/RetentionChart';
import GeoMap from './charts/GeoMap';
import DeviceBreakdown from './charts/DeviceBreakdown';

const POLL_INTERVAL = 30_000;

export default function AnalyticsDashboard({ videoId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('overview');

  useEffect(() => {
    let timer;

    const fetchStats = async () => {
      try {
        const res = await fetch(`/api/analytics/${videoId}/`);
        const data = await res.json();
        setStats(data);
      } catch (err) {
        console.error('[analytics] fetch failed:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    timer = setInterval(fetchStats, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [videoId]);

  if (loading) return <div className="dashboard-skeleton" />;

  return (
    <div className="analytics-dashboard">
      <header className="analytics-dashboard__header">
        <h2>Video Analytics</h2>
        <span className="analytics-dashboard__live">● LIVE</span>
      </header>

      {/* KPI Cards */}
      <div className="kpi-grid">
        {[
          { label: 'Total Views', value: formatNumber(stats?.total_views) },
          { label: 'Watch Time', value: formatDuration(stats?.total_watch_seconds) },
          { label: 'Avg. Retention', value: `${stats?.avg_retention_pct?.toFixed(1)}%` },
          { label: 'Likes', value: formatNumber(stats?.likes) },
          { label: 'Comments', value: formatNumber(stats?.comments) },
          { label: 'Shares', value: formatNumber(stats?.shares) },
        ].map(({ label, value }) => (
          <motion.div
            key={label}
            className="kpi-card"
            whileHover={{ scale: 1.02 }}
          >
            <p className="kpi-card__label">{label}</p>
            <p className="kpi-card__value">{value ?? '—'}</p>
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <nav className="analytics-tabs">
        {['overview', 'retention', 'geography', 'devices'].map((t) => (
          <button
            key={t}
            className={`analytics-tab ${tab === t ? 'analytics-tab--active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {tab === 'overview' && <RetentionChart data={stats?.retention_curve} />}
          {tab === 'retention' && <RetentionChart data={stats?.retention_curve} detailed />}
          {tab === 'geography' && <GeoMap data={stats?.geo_breakdown} />}
          {tab === 'devices' && <DeviceBreakdown data={stats?.device_breakdown} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
