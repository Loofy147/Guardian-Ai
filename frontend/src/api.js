import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Assuming the backend is running on port 8000

/**
 * Fetches a decision from the Guardian AI backend.
 *
 * @param {object} requestData The data to send with the request.
 * @returns {Promise<object>} The decision data from the backend.
 */
export const getDecision = async (requestData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/decide`, requestData);
    return response.data;
  } catch (error) {
    console.error('Error fetching decision:', error);
    throw error;
  }
};

/**
 * Fetches performance metrics for a given problem.
 *
 * @param {string} problemId The ID of the problem to fetch performance for.
 * @returns {Promise<object>} The performance data from the backend.
 */
export const getPerformance = async (problemId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/performance/${problemId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching performance data:', error);
    throw error;
  }
};
