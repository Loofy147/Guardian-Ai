import axios from 'axios';

const apiClient = axios.create({
    baseURL: 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getProblems = () => {
    return apiClient.get('/problems');
};

export const getPerformance = (problemId) => {
    return apiClient.get(`/performance/${problemId}`);
};
