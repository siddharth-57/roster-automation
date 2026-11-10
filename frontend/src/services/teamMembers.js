// Create the API services

import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

// groupNumber is optional: without it, members of all groups are returned
export const getTeamMembers = async (groupNumber) => {
  const response = await axios.get(
    `${API_BASE_URL}/team-members`,
    {
      params: groupNumber
        ? { group_number: groupNumber }
        : {},
    }
  );

  return response.data;
};

// member: { employee_id, name, group_number }
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

export const moveTeamMember = async (employeeId, groupNumber) => {
  const response = await axios.patch(
    `${API_BASE_URL}/team-members/${employeeId}/group`,
    { group_number: groupNumber }
  );

  return response.data;
};