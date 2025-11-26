import React, { useState, useEffect } from 'react';
import { getProblems, getPerformance } from './api';
import PerformanceChart from './PerformanceChart';

const Dashboard = () => {
    const [problems, setProblems] = useState([]);
    const [selectedProblem, setSelectedProblem] = useState(null);
    const [performanceData, setPerformanceData] = useState(null);

    useEffect(() => {
        const fetchProblems = async () => {
            const response = await getProblems();
            setProblems(response.data);
        };
        fetchProblems();
    }, []);

    const handleProblemSelect = async (problemId) => {
        setSelectedProblem(problemId);
        const response = await getPerformance(problemId);
        setPerformanceData(response.data);
    };

    return (
        <div>
            <h1>Dashboard</h1>
            <div>
                <h2>Problems</h2>
                <ul>
                    {problems.map((problem) => (
                        <li key={problem.id} onClick={() => handleProblemSelect(problem.id)}>
                            {problem.problem_type} - {problem.created_at}
                        </li>
                    ))}
                </ul>
            </div>
            {performanceData && (
                <div>
                    <h2>Performance Metrics</h2>
                    <p>Total Decisions: {performanceData.metrics.total_decisions}</p>
                    <p>Total Savings: {performanceData.metrics.total_savings}</p>
                    <PerformanceChart data={performanceData.decisions} />
                </div>
            )}
        </div>
    );
};

export default Dashboard;
