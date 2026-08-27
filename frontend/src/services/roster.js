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


// ------------------------------------------------------
// DOWNLOAD ROSTER
// ------------------------------------------------------

export const downloadRoster = async (
  year,
  month,
  groupNumber
) => {
  const response = await axios.get(
    `${API_BASE_URL}/rosters/${year}/${month}/${groupNumber}/download`,
    {
      responseType: "blob",
    }
  );

  return response;
};


// ------------------------------------------------------
// UPLOAD ROSTER
// ------------------------------------------------------

export const uploadRoster = async (
  year,
  month,
  groupNumber,
  file
) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await axios.post(
    `${API_BASE_URL}/rosters/${year}/${month}/${groupNumber}/upload`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;
};