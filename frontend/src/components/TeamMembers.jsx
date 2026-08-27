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
    <section className="app-section">

      {/* ==================================================
          TEAM MEMBERS HEADER
          ================================================== */}

      <div className="app-section-header">

        <h1>
          Team Members
        </h1>

        <p>
          Manage active team members and
          their roster positions.
        </p>

      </div>


      {/* ==================================================
          ERROR
          ================================================== */}

      {error && (
        <p className="form-error general-error">
          {error}
        </p>
      )}


      {/* ==================================================
          TEAM MEMBERS TABLE
          ================================================== */}

      <div className="members-table-container">

        <table className="members-table">

          <thead>
            <tr>

              <th>
                Position
              </th>

              <th>
                Employee ID
              </th>

              <th>
                Name
              </th>

              <th>
                Action
              </th>

            </tr>
          </thead>


          <tbody>

            {members.map((member) => (
              <tr
                key={
                  member.employee_id
                }
              >

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
                    className="danger-button"
                    onClick={() =>
                      setMemberToDeactivate(
                        member
                      )
                    }
                  >
                    Deactivate
                  </button>

                </td>

              </tr>
            ))}

          </tbody>

        </table>

      </div>


      {/* ==================================================
          DEACTIVATION CONFIRMATION
          ================================================== */}

      {memberToDeactivate && (
        <div className="deactivate-confirmation">

          <h2>
            Deactivate Employee
          </h2>

          <p>
            Are you sure you want to
            deactivate this employee?
          </p>


          <div className="deactivate-details">

            <div className="deactivate-detail">

              <span className="deactivate-detail-label">
                Employee ID
              </span>

              <span className="deactivate-detail-value">
                {
                  memberToDeactivate.employee_id
                }
              </span>

            </div>


            <div className="deactivate-detail">

              <span className="deactivate-detail-label">
                Name
              </span>

              <span className="deactivate-detail-value">
                {
                  memberToDeactivate.name
                }
              </span>

            </div>


            <div className="deactivate-detail">

              <span className="deactivate-detail-label">
                Display Order
              </span>

              <span className="deactivate-detail-value">
                {
                  memberToDeactivate.display_order
                }
              </span>

            </div>

          </div>


          <div className="action-row">

            <button
              className="danger-button"
              onClick={
                handleDeactivate
              }
            >
              I'm Sure
            </button>

            <button
              className="secondary-button"
              onClick={
                handleCancelDeactivate
              }
            >
              No
            </button>

          </div>

        </div>
      )}


      {/* ==================================================
          ADD MEMBER
          ================================================== */}

      <div className="add-member-section">

        <h2 className="subsection-title">
          Add Member
        </h2>


        <form
          className="add-member-form"
          onSubmit={
            handleAddMember
          }
        >

          <div className="form-field">

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


          <div className="form-field">

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


          <button
            className="primary-button"
            type="submit"
          >
            Add Member
          </button>

        </form>

      </div>

    </section>
  );
}


export default TeamMembers;