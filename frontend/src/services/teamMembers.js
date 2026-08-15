// Create the API services

import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

export const getTeamMembers = async () => {
  const response = await axios.get(
    `${API_BASE_URL}/team-members`
  );

  return response.data;
};

export const addTeamMember = async (member) => {
  const response = await axios.post(
    `${API_BASE_URL}/team-members`,
    member
  );

  return response.data;
};

export const deactivateTeamMember = async (employeeId) => {
  const response = await axios.patch(
    `${API_BASE_URL}/team-members/${employeeId}/deactivate`
  );

  return response.data;
};