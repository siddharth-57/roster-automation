// Create Roster setup component

import { useEffect, useState } from "react";

import {
  getActiveTeamMembers,
  validateRoster,
  generateRoster,
} from "../services/roster";

const SHIFTS = ["A", "B", "C", "G", "L", "W"];

function getDaysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function parseDates(value) {
  if (!value.trim()) {
    return [];
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

function normalizeDates(value) {
  const dates = parseDates(value);

  const uniqueDates = [...new Set(dates)];

  return uniqueDates.join(",");
}

function validateDateInput(value, year, month) {
  if (!value.trim()) {
    return "";
  }

  const dates = parseDates(value);
  const daysInMonth = getDaysInMonth(year, month);

  const invalidValues = [];

  for (const date of dates) {
    if (!/^\d+$/.test(date)) {
      invalidValues.push(date);
      continue;
    }

    const day = Number(date);

    if (day < 1 || day > daysInMonth) {
      invalidValues.push(date);
    }
  }

  if (invalidValues.length > 0) {
    return `Invalid date(s): ${invalidValues.join(", ")}`;
  }

  return "";
}

function findMemberConflict(memberRequirements) {
  const datesUsed = {};

  for (const shift of SHIFTS) {
    const dates = parseDates(
      memberRequirements[shift]
    );

    for (const date of dates) {
      if (datesUsed[date]) {
        return (
          `Day ${date} is entered under both ` +
          `${datesUsed[date]} and ${shift}.`
        );
      }

      datesUsed[date] = shift;
    }
  }

  return "";
}

function validateMemberRequirements(
  memberRequirements,
  year,
  month
) {
  for (const shift of SHIFTS) {
    const error = validateDateInput(
      memberRequirements[shift],
      year,
      month
    );

    if (error) {
      return error;
    }
  }

  return findMemberConflict(memberRequirements);
}

function RosterSetup() {
  const [members, setMembers] = useState([]);

  const [year, setYear] = useState(
    new Date().getFullYear()
  );

  const [month, setMonth] = useState(
    new Date().getMonth() + 1
  );

  const [groupNumber, setGroupNumber] = useState("");

  const [publicHolidays, setPublicHolidays] =
    useState(0);

  const [requirements, setRequirements] =
    useState({});

  const [errors, setErrors] = useState({});

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMembers();
  }, []);

  const loadMembers = async () => {
    try {
      const data = await getActiveTeamMembers();

      setMembers(data);

      const initialRequirements = {};

      data.forEach((member) => {
        initialRequirements[member.employee_id] = {
          A: "",
          B: "",
          C: "",
          G: "",
          L: "",
          W: "",
        };
      });

      setRequirements(initialRequirements);
    } catch (error) {
      console.error(
        "Failed to load team members:",
        error
      );

      setErrors({
        general: "Failed to load team members.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateRoster = async () => {
    if (hasErrors) {
      return;
    }
  
    const formattedRequirements = members.map(
      (member) => {
        const memberRequirements =
          requirements[member.employee_id];
      
        return {
          employee_id: member.employee_id,
          a: parseDates(memberRequirements.A).map(Number),
          b: parseDates(memberRequirements.B).map(Number),
          c: parseDates(memberRequirements.C).map(Number),
          g: parseDates(memberRequirements.G).map(Number),
          l: parseDates(memberRequirements.L).map(Number),
          w: parseDates(memberRequirements.W).map(Number),
        };
      }
    );
  
    const request = {
      year,
      month,
      group_number: groupNumber.trim(),
      public_holidays: publicHolidays,
      requirements: formattedRequirements,
    };
  
    try {
      // --------------------------------------------------
      // 1. Validate the roster requirements.
      // --------------------------------------------------
      const validationResponse = await validateRoster(
        request
      );
    
      console.log(
        "Roster validation successful:",
        validationResponse
      );
    
      // --------------------------------------------------
      // 2. Generate and persist the roster.
      // --------------------------------------------------
      const generationResponse = await generateRoster(
        request
      );
    
      console.log(
        "Roster generation successful:",
        generationResponse
      );
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Failed to generate roster.";
    
      setErrors((previous) => ({
        ...previous,
        general: message,
      }));
    }
  };



  const updateMemberError = (
    employeeId,
    updatedRequirements
  ) => {
    const error = validateMemberRequirements(
      updatedRequirements,
      year,
      month
    );

    setErrors((previous) => ({
      ...previous,
      [employeeId]: error,
    }));
  };

  const handleRequirementChange = (
    employeeId,
    shift,
    value
  ) => {
    const updatedMemberRequirements = {
      ...requirements[employeeId],
      [shift]: value,
    };

    setRequirements((previous) => ({
      ...previous,
      [employeeId]: updatedMemberRequirements,
    }));

    updateMemberError(
      employeeId,
      updatedMemberRequirements
    );
  };

  const handleRequirementBlur = (
    employeeId,
    shift
  ) => {
    const currentValue =
      requirements[employeeId][shift];

    const normalizedValue =
      normalizeDates(currentValue);

    const updatedMemberRequirements = {
      ...requirements[employeeId],
      [shift]: normalizedValue,
    };

    setRequirements((previous) => ({
      ...previous,
      [employeeId]: updatedMemberRequirements,
    }));

    updateMemberError(
      employeeId,
      updatedMemberRequirements
    );
  };

  const revalidateAllMembers = (
    newYear,
    newMonth
  ) => {
    const updatedErrors = {};

    members.forEach((member) => {
      const memberRequirements =
        requirements[member.employee_id];

      if (!memberRequirements) {
        return;
      }

      updatedErrors[member.employee_id] =
        validateMemberRequirements(
          memberRequirements,
          newYear,
          newMonth
        );
    });

    setErrors((previous) => ({
      ...previous,
      ...updatedErrors,
    }));
  };

  const handleYearChange = (event) => {
    const newYear = Number(
      event.target.value
    );

    setYear(newYear);

    revalidateAllMembers(
      newYear,
      month
    );
  };

  const handleMonthChange = (event) => {
    const newMonth = Number(
      event.target.value
    );

    setMonth(newMonth);

    revalidateAllMembers(
      year,
      newMonth
    );
  };

  const hasErrors = Object.entries(
    errors
  ).some(
    ([key, value]) =>
      key !== "general" && value
  );

  if (loading) {
    return <p>Loading team members...</p>;
  }

  return (
    <div>
      <h1>Create Monthly Roster</h1>

      {errors.general && (
        <p>{errors.general}</p>
      )}

      <div>
        <label>
          Month:

          <select
            value={month}
            onChange={handleMonthChange}
          >
            {Array.from(
              { length: 12 },
              (_, index) => index + 1
            ).map((monthNumber) => (
              <option
                key={monthNumber}
                value={monthNumber}
              >
                {monthNumber}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div>
        <label>
          Year:

          <input
            type="number"
            value={year}
            onChange={handleYearChange}
          />
        </label>
      </div>

      <div>
        <label>
          Group Number:

          <input
            type="text"
            value={groupNumber}
            onChange={(event) =>
              setGroupNumber(
                event.target.value
              )
            }
          />
        </label>
      </div>

      <div>
        <label>
          Public Holidays:

          <input
            type="number"
            min="0"
            value={publicHolidays}
            onChange={(event) =>
              setPublicHolidays(
                Number(event.target.value)
              )
            }
          />
        </label>
      </div>

      <h2>Member Requirements</h2>

      <table>
        <thead>
          <tr>
            <th>Member</th>

            {SHIFTS.map((shift) => (
              <th key={shift}>
                {shift}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {members.map((member) => (
            <tr
              key={member.employee_id}
            >
              <td>
                {member.name}
              </td>

              {SHIFTS.map((shift) => (
                <td key={shift}>
                  <input
                    type="text"
                    placeholder="e.g. 2,5,8"
                    value={
                      requirements[
                        member.employee_id
                      ]?.[shift] || ""
                    }
                    onChange={(event) =>
                      handleRequirementChange(
                        member.employee_id,
                        shift,
                        event.target.value
                      )
                    }
                    onBlur={() =>
                      handleRequirementBlur(
                        member.employee_id,
                        shift
                      )
                    }
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {Object.entries(errors)
        .filter(
          ([key, value]) =>
            key !== "general" && value
        )
        .map(
          ([employeeId, error]) => (
            <p key={employeeId}>
              {employeeId}: {error}
            </p>
          )
        )}

      <button
        disabled={
          hasErrors ||
          !groupNumber.trim()
        }
        onClick={handleGenerateRoster}
      >
        Generate Roster
      </button>
    </div>
  );
}

export default RosterSetup;