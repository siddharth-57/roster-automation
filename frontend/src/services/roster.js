import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

export const getActiveTeamMembers = async () => {
  const response = await axios.get(
    `${API_BASE_URL}/team-members`
  );

  return response.data;
};

export const validateRoster = async (rosterRequest) => {
  const response = await axios.post(
    `${API_BASE_URL}/rosters/validate`,
    rosterRequest
  );

  return response.data;
};

export const generateRoster = async (rosterRequest) => {
  const response = await axios.post(
    `${API_BASE_URL}/rosters/generate`,
    rosterRequest
  );

  return response.data;
};