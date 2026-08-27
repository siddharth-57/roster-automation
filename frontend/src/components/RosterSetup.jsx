// Create Roster setup component

import { useEffect, useState } from "react";

import {
  getActiveTeamMembers,
  validateRoster,
  generateRoster,
  downloadRoster,
  uploadRoster,
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

  const daysInMonth = getDaysInMonth(
    year,
    month
  );

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

  return findMemberConflict(
    memberRequirements
  );
}


function RosterSetup() {
  // --------------------------------------------------
  // CREATE ROSTER STATE
  // --------------------------------------------------

  const [members, setMembers] = useState([]);

  const [year, setYear] = useState(
    new Date().getFullYear()
  );

  const [month, setMonth] = useState(
    new Date().getMonth() + 1
  );

  const [groupNumber, setGroupNumber] =
    useState("");

  const [publicHolidays, setPublicHolidays] =
    useState(0);

  const [requirements, setRequirements] =
    useState({});

  const [errors, setErrors] = useState({});

  const [loading, setLoading] = useState(true);

  const [rosterStatus, setRosterStatus] =
    useState(null);


  // --------------------------------------------------
  // DOWNLOAD / UPLOAD ROSTER STATE
  // --------------------------------------------------

  const [fileMonth, setFileMonth] = useState(
    new Date().getMonth() + 1
  );

  const [fileYear, setFileYear] = useState(
    new Date().getFullYear()
  );

  const [fileGroupNumber, setFileGroupNumber] =
    useState("");

  const [selectedFile, setSelectedFile] =
    useState(null);

  const [fileStatus, setFileStatus] =
    useState(null);

  const [uploading, setUploading] =
    useState(false);

  const [downloading, setDownloading] =
    useState(false);


  // --------------------------------------------------
  // LOAD TEAM MEMBERS
  // --------------------------------------------------

  useEffect(() => {
    loadMembers();
  }, []);


  const loadMembers = async () => {
    try {
      const data = await getActiveTeamMembers();

      setMembers(data);

      const initialRequirements = {};

      data.forEach((member) => {
        initialRequirements[
          member.employee_id
        ] = {
          A: "",
          B: "",
          C: "",
          G: "",
          L: "",
          W: "",
        };
      });

      setRequirements(
        initialRequirements
      );

    } catch (error) {
      console.error(
        "Failed to load team members:",
        error
      );

      setErrors({
        general:
          "Failed to load team members.",
      });

    } finally {
      setLoading(false);
    }
  };


  // --------------------------------------------------
  // GENERATE ROSTER
  // --------------------------------------------------

  const handleGenerateRoster = async () => {
    if (hasErrors) {
      return;
    }

    setRosterStatus(null);

    const formattedRequirements =
      members.map((member) => {
        const memberRequirements =
          requirements[
            member.employee_id
          ];

        return {
          employee_id:
            member.employee_id,

          a: parseDates(
            memberRequirements.A
          ).map(Number),

          b: parseDates(
            memberRequirements.B
          ).map(Number),

          c: parseDates(
            memberRequirements.C
          ).map(Number),

          g: parseDates(
            memberRequirements.G
          ).map(Number),

          l: parseDates(
            memberRequirements.L
          ).map(Number),

          w: parseDates(
            memberRequirements.W
          ).map(Number),
        };
      });


    const request = {
      year,
      month,
      group_number:
        groupNumber.trim(),
      public_holidays:
        publicHolidays,
      requirements:
        formattedRequirements,
    };


    try {
      // --------------------------------------------------
      // 1. Validate roster requirements
      // --------------------------------------------------

      const validationResponse =
        await validateRoster(
          request
        );

      console.log(
        "Roster validation successful:",
        validationResponse
      );


      // --------------------------------------------------
      // 2. Generate and persist roster
      // --------------------------------------------------

      const generationResponse =
        await generateRoster(
          request
        );

      console.log(
        "Roster generation successful:",
        generationResponse
      );


      // --------------------------------------------------
      // 3. Store status information
      // --------------------------------------------------

      setRosterStatus({
        type: "success",

        message:
          generationResponse.message ||
          "Roster generated successfully",

        rosterId:
          generationResponse.roster_id,

        rosterName:
          generationResponse.roster_name,

        warnings:
          generationResponse.warnings ||
          [],

        relaxedRequirements:
          generationResponse
            .relaxed_requirements ||
          [],
      });


      setErrors((previous) => ({
        ...previous,
        general: "",
      }));

    } catch (error) {
      const statusCode =
        error.response?.status;

      const detail =
        error.response?.data?.detail;


      // --------------------------------------------------
      // Duplicate roster
      // --------------------------------------------------

      if (statusCode === 409) {
        setRosterStatus({
          type: "duplicate",

          message:
            typeof detail === "string"
              ? detail
              : "Roster already exists.",
        });

        return;
      }


      // --------------------------------------------------
      // Other generation errors
      // --------------------------------------------------

      const message =
        typeof detail === "string"
          ? detail
          : "Failed to generate roster.";


      setRosterStatus({
        type: "error",
        message,
      });
    }
  };


  // --------------------------------------------------
  // REQUIREMENT VALIDATION
  // --------------------------------------------------

  const updateMemberError = (
    employeeId,
    updatedRequirements
  ) => {
    const error =
      validateMemberRequirements(
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
      [employeeId]:
        updatedMemberRequirements,
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
      requirements[
        employeeId
      ][shift];

    const normalizedValue =
      normalizeDates(currentValue);

    const updatedMemberRequirements = {
      ...requirements[employeeId],
      [shift]: normalizedValue,
    };

    setRequirements((previous) => ({
      ...previous,
      [employeeId]:
        updatedMemberRequirements,
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
        requirements[
          member.employee_id
        ];

      if (!memberRequirements) {
        return;
      }

      updatedErrors[
        member.employee_id
      ] = validateMemberRequirements(
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


  const handleYearChange = (
    event
  ) => {
    const newYear = Number(
      event.target.value
    );

    setYear(newYear);

    revalidateAllMembers(
      newYear,
      month
    );
  };


  const handleMonthChange = (
    event
  ) => {
    const newMonth = Number(
      event.target.value
    );

    setMonth(newMonth);

    revalidateAllMembers(
      year,
      newMonth
    );
  };


  const hasErrors =
    Object.entries(errors).some(
      ([key, value]) =>
        key !== "general" && value
    );


  // --------------------------------------------------
  // DOWNLOAD ROSTER
  // --------------------------------------------------

  const handleDownloadRoster =
    async () => {

      setFileStatus(null);

      if (
        !fileGroupNumber.trim()
      ) {
        setFileStatus({
          type: "error",
          message:
            "Please enter a group number.",
        });

        return;
      }

      try {
        setDownloading(true);

        const response =
          await downloadRoster(
            fileYear,
            fileMonth,
            fileGroupNumber.trim()
          );


        // --------------------------------------------------
        // Create downloadable browser file
        // --------------------------------------------------

        const blob =
          new Blob(
            [response.data],
            {
              type:
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
          );

        const url =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement(
            "a"
          );

        link.href = url;

        link.download =
          `${fileYear}-${String(
            fileMonth
          ).padStart(2, "0")}-Group-${fileGroupNumber.trim()}.xlsx`;

        document.body.appendChild(
          link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
          url
        );


        setFileStatus({
          type: "success",
          message:
            "Roster downloaded successfully.",
        });

      } catch (error) {
        const statusCode =
          error.response?.status;

        const detail =
          error.response?.data?.detail;


        if (statusCode === 404) {
          setFileStatus({
            type: "error",
            message:
              typeof detail === "string"
                ? detail
                : "Roster does not exist.",
          });

          return;
        }


        setFileStatus({
          type: "error",
          message:
            typeof detail === "string"
              ? detail
              : "Failed to download roster.",
        });

      } finally {
        setDownloading(false);
      }
    };


  // --------------------------------------------------
  // UPLOAD ROSTER
  // --------------------------------------------------

  const handleUploadRoster =
    async () => {

      setFileStatus(null);


      if (
        !fileGroupNumber.trim()
      ) {
        setFileStatus({
          type: "error",
          message:
            "Please enter a group number.",
        });

        return;
      }


      if (!selectedFile) {
        setFileStatus({
          type: "error",
          message:
            "Please select an Excel file.",
        });

        return;
      }


      if (
        !selectedFile.name
          .toLowerCase()
          .endsWith(".xlsx")
      ) {
        setFileStatus({
          type: "error",
          message:
            "Please select an .xlsx Excel file.",
        });

        return;
      }


      try {
        setUploading(true);


        const response =
          await uploadRoster(
            fileYear,
            fileMonth,
            fileGroupNumber.trim(),
            selectedFile
          );


        if (
          response.action === "created"
        ) {
          setFileStatus({
            type: "success",
            message:
              `Roster ${response.roster_name} uploaded successfully and created in the database.`,
          });

        } else if (
          response.action ===
          "overwritten"
        ) {
          setFileStatus({
            type: "success",
            message:
              `Roster ${response.roster_name} uploaded successfully and the existing roster was overwritten.`,
          });

        } else {
          setFileStatus({
            type: "success",
            message:
              response.message ||
              "Roster uploaded successfully.",
          });
        }


        // Clear selected file after
        // successful upload.
        setSelectedFile(null);


        // Reset the file input.
        const fileInput =
          document.getElementById(
            "roster-upload-file"
          );

        if (fileInput) {
          fileInput.value = "";
        }

      } catch (error) {
        const statusCode =
          error.response?.status;

        const detail =
          error.response?.data?.detail;


        if (statusCode === 400) {
          setFileStatus({
            type: "error",
            message:
              typeof detail === "string"
                ? detail
                : "The roster could not be uploaded.",
          });

          return;
        }


        setFileStatus({
          type: "error",
          message:
            typeof detail === "string"
              ? detail
              : "Failed to upload roster.",
        });

      } finally {
        setUploading(false);
      }
    };


  // --------------------------------------------------
  // LOADING
  // --------------------------------------------------

  if (loading) {
    return (
      <p>
        Loading team members...
      </p>
    );
  }


  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <div className="roster-page">

      {/* ==================================================
          CREATE MONTHLY ROSTER
          ================================================== */}

      <section className="app-section">

        <div className="app-section-header">
          <h1>
            Create Monthly Roster
          </h1>

          <p>
            Configure the monthly roster and
            member shift requirements.
          </p>
        </div>


        {errors.general && (
          <p className="form-error general-error">
            {errors.general}
          </p>
        )}


        {/* --------------------------------------------------
            ROSTER DETAILS
            -------------------------------------------------- */}

        <div className="form-grid">

          <div className="form-field">
            <label>
              Month:

              <select
                value={month}
                onChange={
                  handleMonthChange
                }
              >
                {Array.from(
                  { length: 12 },
                  (_, index) =>
                    index + 1
                ).map(
                  (monthNumber) => (
                    <option
                      key={monthNumber}
                      value={monthNumber}
                    >
                      {monthNumber}
                    </option>
                  )
                )}
              </select>
            </label>
          </div>


          <div className="form-field">
            <label>
              Year:

              <input
                type="number"
                value={year}
                onChange={
                  handleYearChange
                }
              />
            </label>
          </div>


          <div className="form-field">
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


          <div className="form-field">
            <label>
              Public Holidays:

              <input
                type="number"
                min="0"
                value={
                  publicHolidays
                }
                onChange={(event) =>
                  setPublicHolidays(
                    Number(
                      event.target.value
                    )
                  )
                }
              />
            </label>
          </div>

        </div>


        {/* --------------------------------------------------
            MEMBER REQUIREMENTS
            -------------------------------------------------- */}

        <h2 className="subsection-title">
          Member Requirements
        </h2>


        <div className="table-container">

          <table className="requirements-table">

            <thead>
              <tr>
                <th>
                  Member
                </th>

                {SHIFTS.map(
                  (shift) => (
                    <th
                      key={shift}
                    >
                      {shift}
                    </th>
                  )
                )}
              </tr>
            </thead>


            <tbody>

              {members.map(
                (member) => (
                  <tr
                    key={
                      member.employee_id
                    }
                  >

                    <td>
                      {member.name}
                    </td>


                    {SHIFTS.map(
                      (shift) => (
                        <td
                          key={shift}
                        >
                          <input
                            type="text"
                            placeholder="e.g. 2,5,8"
                            value={
                              requirements[
                                member.employee_id
                              ]?.[
                                shift
                              ] || ""
                            }
                            onChange={(
                              event
                            ) =>
                              handleRequirementChange(
                                member.employee_id,
                                shift,
                                event
                                  .target
                                  .value
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
                      )
                    )}

                  </tr>
                )
              )}

            </tbody>

          </table>

        </div>


        {/* --------------------------------------------------
            VALIDATION ERRORS
            -------------------------------------------------- */}

        {Object.entries(
          errors
        )
          .filter(
            ([key, value]) =>
              key !== "general" &&
              value
          )
          .map(
            ([
              employeeId,
              error,
            ]) => (
              <p
                key={employeeId}
                className="form-error"
              >
                {employeeId}:{" "}
                {error}
              </p>
            )
          )}


        {/* --------------------------------------------------
            GENERATE BUTTON
            -------------------------------------------------- */}

        <div className="action-row">

          <button
            className="primary-button"
            disabled={
              hasErrors ||
              !groupNumber.trim()
            }
            onClick={
              handleGenerateRoster
            }
          >
            Generate Roster
          </button>

        </div>


        {/* ==================================================
            ROSTER STATUS
            ================================================== */}

        {rosterStatus && (
          <div
            className={`roster-status-box ${rosterStatus.type}`}
          >

            <div className="roster-status-header">

              {rosterStatus.type ===
                "success" && (
                <>
                  <span className="status-icon">
                    ✓
                  </span>

                  <h2>
                    Roster Generated
                    Successfully
                  </h2>
                </>
              )}


              {rosterStatus.type ===
                "duplicate" && (
                <>
                  <span className="status-icon">
                    ⚠
                  </span>

                  <h2>
                    Roster Already
                    Exists
                  </h2>
                </>
              )}


              {rosterStatus.type ===
                "error" && (
                <>
                  <span className="status-icon">
                    ✕
                  </span>

                  <h2>
                    Roster Generation
                    Failed
                  </h2>
                </>
              )}

            </div>


            <div className="roster-status-content">

              {rosterStatus.type ===
                "success" && (
                <>

                  <p className="status-message">
                    {
                      rosterStatus.message
                    }
                  </p>


                  <div className="roster-details">

                    <div className="roster-detail">

                      <span className="detail-label">
                        Roster Name
                      </span>

                      <span className="detail-value">
                        {
                          rosterStatus.rosterName
                        }
                      </span>

                    </div>


                    <div className="roster-detail">

                      <span className="detail-label">
                        Roster ID
                      </span>

                      <span className="detail-value">
                        {
                          rosterStatus.rosterId
                        }
                      </span>

                    </div>

                  </div>


                  {rosterStatus.warnings.length >
                    0 && (
                    <div className="status-section warnings-section">

                      <h3>
                        Warnings
                      </h3>

                      <ul>
                        {
                          rosterStatus.warnings.map(
                            (
                              warning,
                              index
                            ) => (
                              <li
                                key={
                                  index
                                }
                              >
                                {
                                  warning
                                }
                              </li>
                            )
                          )
                        }
                      </ul>

                    </div>
                  )}


                  {rosterStatus.relaxedRequirements.length >
                    0 && (
                    <div className="status-section relaxed-section">

                      <h3>
                        Relaxed
                        Requirements
                      </h3>

                      <ul>
                        {
                          rosterStatus.relaxedRequirements.map(
                            (
                              requirement,
                              index
                            ) => (
                              <li
                                key={
                                  index
                                }
                              >
                                {
                                  typeof requirement ===
                                  "string"
                                    ? requirement
                                    : JSON.stringify(
                                        requirement
                                      )
                                }
                              </li>
                            )
                          )
                        }
                      </ul>

                    </div>
                  )}


                  {
                    rosterStatus.warnings
                      .length ===
                      0 &&
                    rosterStatus.relaxedRequirements
                      .length ===
                      0 && (
                      <p className="status-clean">
                        No warnings or
                        relaxed
                        requirements.
                      </p>
                    )
                  }

                </>
              )}


              {rosterStatus.type ===
                "duplicate" && (
                <p className="status-message">
                  {
                    rosterStatus.message
                  }
                </p>
              )}


              {rosterStatus.type ===
                "error" && (
                <p className="status-message">
                  {
                    rosterStatus.message
                  }
                </p>
              )}

            </div>

          </div>
        )}

      </section>


      {/* ==================================================
          DOWNLOAD / UPLOAD ROSTER
          ================================================== */}

      <section className="app-section">

        <div className="app-section-header">

          <h1>
            Download / Upload Roster
          </h1>

          <p>
            Upload an existing Excel roster
            or download a roster from the
            database.
          </p>

        </div>


        {/* --------------------------------------------------
            FILE ROSTER DETAILS
            -------------------------------------------------- */}

        <div className="form-grid">

          <div className="form-field">
            <label>
              Month:

              <select
                value={fileMonth}
                onChange={(event) =>
                  setFileMonth(
                    Number(
                      event.target.value
                    )
                  )
                }
              >
                {Array.from(
                  { length: 12 },
                  (_, index) =>
                    index + 1
                ).map(
                  (monthNumber) => (
                    <option
                      key={monthNumber}
                      value={monthNumber}
                    >
                      {monthNumber}
                    </option>
                  )
                )}
              </select>
            </label>
          </div>


          <div className="form-field">
            <label>
              Year:

              <input
                type="number"
                value={fileYear}
                onChange={(event) =>
                  setFileYear(
                    Number(
                      event.target.value
                    )
                  )
                }
              />
            </label>
          </div>


          <div className="form-field">
            <label>
              Group Number:

              <input
                type="text"
                value={
                  fileGroupNumber
                }
                onChange={(event) =>
                  setFileGroupNumber(
                    event.target.value
                  )
                }
              />
            </label>
          </div>

        </div>


        {/* --------------------------------------------------
            FILE UPLOAD
            -------------------------------------------------- */}

        <div className="file-upload">

          <label>
            Excel File:

            <input
              id="roster-upload-file"
              type="file"
              accept=".xlsx"
              onChange={(event) =>
                setSelectedFile(
                  event.target.files?.[0] ||
                  null
                )
              }
            />

          </label>

        </div>


        {/* --------------------------------------------------
            UPLOAD / DOWNLOAD BUTTONS
            -------------------------------------------------- */}

        <div className="action-row">

          <button
            className="primary-button"
            onClick={
              handleUploadRoster
            }
            disabled={
              uploading ||
              downloading
            }
          >
            {uploading
              ? "Uploading..."
              : "Upload"}
          </button>


          <button
            className="secondary-button"
            onClick={
              handleDownloadRoster
            }
            disabled={
              uploading ||
              downloading
            }
          >
            {downloading
              ? "Downloading..."
              : "Download"}
          </button>

        </div>


        {/* ==================================================
            FILE STATUS
            ================================================== */}

        {fileStatus && (
          <div
            className={`roster-status-box ${fileStatus.type}`}
          >

            <div className="roster-status-header">

              {fileStatus.type ===
                "success" && (
                <>
                  <span className="status-icon">
                    ✓
                  </span>

                  <h2>
                    Success
                  </h2>
                </>
              )}


              {fileStatus.type ===
                "error" && (
                <>
                  <span className="status-icon">
                    ✕
                  </span>

                  <h2>
                    Operation Failed
                  </h2>
                </>
              )}

            </div>


            <div className="roster-status-content">

              <p className="status-message">
                {
                  fileStatus.message
                }
              </p>

            </div>

          </div>
        )}

      </section>

    </div>
  );
}


export default RosterSetup;