import React, { useState, useEffect } from 'react';
import { getDecision, getPerformance } from './api';
import PerformanceChart from './PerformanceChart';
import './App.css';

const Dashboard = () => {
  const [decision, setDecision] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // --- Fetch Decision ---
        // In a real app, this data would come from a user's configuration
        const decisionRequest = {
          user_id: '123e4567-e89b-12d3-a456-426614174000',
          problem_type: 'ski_rental',
          historical_data: [
            { timestamp: '2023-01-01T00:00:00Z', value: 100 },
            { timestamp: '2023-01-01T01:00:00Z', value: 110 },
            // ... more data points
          ],
          problem_params: { commit_cost: 500, step_cost: 10 },
          decision_state: { current_step: 30 },
          trust_level: 0.8,
        };
        const decisionData = await getDecision(decisionRequest);
        setDecision(decisionData);

        // --- Fetch Performance ---
        // This would also be dynamic in a real application
        if (decisionData.problem_id) {
          const performanceData = await getPerformance(decisionData.problem_id);
          setPerformance(performanceData);
        }

      } catch (err) {
        setError('Failed to fetch data from the backend. Please ensure the backend is running.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Guardian AI - Cloud Scaling</h1>
      </header>
      <main className="dashboard-main">
        <div className="decision-panel">
          <h2>Current Recommendation</h2>
          <div className="recommendation">
            <p className="action">{decision?.action?.replace('_', ' ').toUpperCase()}</p>
            <p className="confidence">Confidence: {decision ? (decision.uncertainty < 20 ? 'High' : 'Medium') : 'N/A'}</p>
          </div>
          <p className="savings">Expected Savings: $2,340/month</p>
          <div className="reasoning">
            <h3>Why?</h3>
            <ul>
              <li>Predicted usage: {decision?.prediction.toFixed(2)} hours/month</li>
              <li>Uncertainty: ±{decision?.uncertainty.toFixed(2)} hours</li>
              <li>Reserve threshold: (Calculated dynamically)</li>
            </ul>
          </div>
          <div className="guarantee">
            <h3>Worst-case guarantee:</h3>
            <p>Even if prediction is wrong, cost ≤ {decision?.guarantee.toFixed(2)}x optimal</p>
          </div>
          <div className="controls">
            <button>Override</button>
            <button>Trust More</button>
            <button>Trust Less</button>
          </div>
        </div>
        <div className="performance-panel">
          <h2>Historical Performance</h2>
          {performance ? (
            <>
              <div className="metrics">
                <p>Actual savings vs. static strategy: {performance.metrics.total_savings.toFixed(2)}</p>
                <p>Times ML was wrong: (Not implemented)</p>
                <p>Cost when wrong: (Not implemented)</p>
                <p>Average Competitive Ratio: {performance.metrics.average_competitive_ratio.toFixed(2)}</p>
              </div>
              <PerformanceChart data={performance.metrics} />
            </>
          ) : (
            <p>No performance data available.</p>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
