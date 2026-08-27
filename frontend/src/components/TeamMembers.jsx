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

  const [error, setError] = useState("");

  const [memberToDeactivate, setMemberToDeactivate] =
    useState(null);


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
      });

      setEmployeeId("");
      setName("");

      await loadMembers();
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Failed to add team member.";

      setError(message);
    }
  };


  const handleDeactivate = async () => {
    if (!memberToDeactivate) {
      return;
    }

    setError("");

    try {
      await deactivateTeamMember(
        memberToDeactivate.employee_id
      );

      setMemberToDeactivate(null);

      await loadMembers();
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Failed to deactivate team member.";

      setError(message);
    }
  };


  const handleCancelDeactivate = () => {
    setMemberToDeactivate(null);
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
              <td>
                {member.display_order}
              </td>

              <td>
                {member.employee_id}
              </td>

              <td>
                {member.name}
              </td>

              <td>
                <button
                  onClick={() =>
                    setMemberToDeactivate(member)
                  }
                >
                  Deactivate
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>


      {memberToDeactivate && (
        <div>
          <h2>
            Deactivate Employee
          </h2>

          <p>
            Are you sure you want to
            deactivate this employee?
          </p>

          <p>
            <strong>
              Employee ID:
            </strong>{" "}
            {memberToDeactivate.employee_id}
          </p>

          <p>
            <strong>
              Name:
            </strong>{" "}
            {memberToDeactivate.name}
          </p>

          <p>
            <strong>
              Display Order:
            </strong>{" "}
            {memberToDeactivate.display_order}
          </p>

          <button
            onClick={handleDeactivate}
          >
            I'm Sure
          </button>

          <button
            onClick={handleCancelDeactivate}
          >
            No
          </button>
        </div>
      )}

      <h2>Add Member</h2>

      <form onSubmit={handleAddMember}>
        <div>
          <label>
            Employee ID:

            <input
              type="text"
              value={employeeId}
              onChange={(event) =>
                setEmployeeId(
                  event.target.value
                )
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
                setName(
                  event.target.value
                )
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