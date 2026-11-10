// Group API services + a tiny "something changed" signal,
// so the roster screen refreshes its dropdowns and member list
// when groups or members are changed on the Team Members page.

import axios from "axios";

const API_BASE_URL = "http://localhost:8000";


// --------------------------------------------------
// CHANGE NOTIFICATIONS
// --------------------------------------------------

export const GROUPS_CHANGED_EVENT = "roster:groups-changed";
export const MEMBERS_CHANGED_EVENT = "roster:members-changed";

export const notifyGroupsChanged = () =>
  window.dispatchEvent(new Event(GROUPS_CHANGED_EVENT));

export const notifyMembersChanged = () =>
  window.dispatchEvent(new Event(MEMBERS_CHANGED_EVENT));


// --------------------------------------------------
// DISPLAY HELPER
// --------------------------------------------------

// "08", "08 – Night Ops", "99 (inactive)"
export const formatGroupLabel = (group) => {
  const label = group.name
    ? `${group.group_number} – ${group.name}`
    : group.group_number;

  return group.active ? label : `${label} (inactive)`;
};


// --------------------------------------------------
// API
// --------------------------------------------------

export const getGroups = async (includeInactive = false) => {
  const response = await axios.get(
    `${API_BASE_URL}/groups`,
    {
      params: {
        include_inactive: includeInactive,
      },
    }
  );

  return response.data;
};


export const createGroup = async (group) => {
  const response = await axios.post(
    `${API_BASE_URL}/groups`,
    group
  );

  return response.data;
};


export const renameGroup = async (groupNumber, name) => {
  const response = await axios.patch(
    `${API_BASE_URL}/groups/${encodeURIComponent(groupNumber)}`,
    { name }
  );

  return response.data;
};


export const deactivateGroup = async (groupNumber) => {
  const response = await axios.patch(
    `${API_BASE_URL}/groups/${encodeURIComponent(groupNumber)}/deactivate`
  );

  return response.data;
};


export const activateGroup = async (groupNumber) => {
  const response = await axios.patch(
    `${API_BASE_URL}/groups/${encodeURIComponent(groupNumber)}/activate`
  );

  return response.data;
};