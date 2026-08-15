// Team Members component

import { useEffect, useState } from "react";

import {
  getTeamMembers,
  addTeamMember,
  deactivateTeamMember,
} from "../services/teamMembers";


function TeamMembers() {
  const [members, setMembers] = useState([]);

  const [employeeId, setEmployeeId] = useState("");
  const [name, setName] = useState("");
  const [position, setPosition] = useState("");

  const [error, setError] = useState("");


  const loadMembers = async () => {
    try {
      const data = await getTeamMembers();
      setMembers(data);
      setError("");
    } catch (error) {
      setError("Failed to load team members.");
    }
  };


  useEffect(() => {
    loadMembers();
  }, []);


  const handleAddMember = async (event) => {
    event.preventDefault();

    setError("");

    try {
      await addTeamMember({
        employee_id: employeeId,
        name: name,
        display_order: Number(position),
      });

      setEmployeeId("");
      setName("");
      setPosition("");

      await loadMembers();
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Failed to add team member.";

      setError(message);
    }
  };


  const handleDeactivate = async (employeeId) => {
    try {
      await deactivateTeamMember(employeeId);
      await loadMembers();
    } catch (error) {
      setError("Failed to remove team member.");
    }
  };


  return (
    <div>
      <h1>Team Members</h1>

      {error && (
        <p>
          {error}
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>Position</th>
            <th>Employee ID</th>
            <th>Name</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          {members.map((member) => (
            <tr key={member.employee_id}>
              <td>{member.display_order}</td>
              <td>{member.employee_id}</td>
              <td>{member.name}</td>

              <td>
                <button
                  onClick={() =>
                    handleDeactivate(member.employee_id)
                  }
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>


      <h2>Add Member</h2>

      <form onSubmit={handleAddMember}>
        <div>
          <label>
            Employee ID:
            <input
              type="text"
              value={employeeId}
              onChange={(event) =>
                setEmployeeId(event.target.value)
              }
              required
            />
          </label>
        </div>

        <div>
          <label>
            Name:
            <input
              type="text"
              value={name}
              onChange={(event) =>
                setName(event.target.value)
              }
              required
            />
          </label>
        </div>

        <div>
          <label>
            Position:
            <input
              type="number"
              min="1"
              value={position}
              onChange={(event) =>
                setPosition(event.target.value)
              }
              required
            />
          </label>
        </div>

        <button type="submit">
          Add Member
        </button>
      </form>
    </div>
  );
}

export default TeamMembers;