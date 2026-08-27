// Team Members component
// UI theme is controlled by App.css; application logic is unchanged.

import { useEffect, useState } from "react";

import {
  getTeamMembers,
  addTeamMember,
  deactivateTeamMember,
} from "../services/teamMembers";

import {
  AlertTriangle,
  Plus,
  UserPlus,
  UserX,
  Users,
} from "lucide-react";

import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";


function TeamMembers() {
  const [members, setMembers] = useState([]);

  const [employeeId, setEmployeeId] =
    useState("");

  const [name, setName] =
    useState("");

  const [error, setError] =
    useState("");

  const [memberToDeactivate, setMemberToDeactivate] =
    useState(null);


  const loadMembers = async () => {
    try {
      const data = await getTeamMembers();

      setMembers(data);
      setError("");

    } catch (error) {
      setError(
        "Failed to load team members."
      );
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

        <Stack
          direction="row"
          alignItems="center"
          spacing={1.5}
        >

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 42,
              height: 42,
              borderRadius: "11px",
              background: "#f3e8ff",
              color: "#7c3aed",
            }}
          >
            <Users size={22} />
          </Box>

          <Box>
            <h1>
              Team Members
            </h1>

            <p>
              Manage active team members and
              their roster positions.
            </p>
          </Box>

        </Stack>

      </div>


      {/* ==================================================
          ERROR
          ================================================== */}

      {error && (
        <Alert
          severity="error"
          icon={<AlertTriangle size={19} />}
          sx={{
            mb: 3,
            borderRadius: "9px",
          }}
        >
          {error}
        </Alert>
      )}


      {/* ==================================================
          TEAM MEMBERS TABLE
          ================================================== */}

      <TableContainer
        component={Paper}
        elevation={0}
        sx={{
          border: "1px solid #e7ddf0",
          borderRadius: "11px",
          overflow: "hidden",
          mb: 4,
        }}
      >

        <Table>

          <TableHead>

            <TableRow
              sx={{
                backgroundColor: "#faf7fd",
              }}
            >

              <TableCell
                sx={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#4b3a58",
                  textTransform: "uppercase",
                  letterSpacing: "0.4px",
                }}
              >
                Position
              </TableCell>


              <TableCell
                sx={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#4b3a58",
                  textTransform: "uppercase",
                  letterSpacing: "0.4px",
                }}
              >
                Employee ID
              </TableCell>


              <TableCell
                sx={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#4b3a58",
                  textTransform: "uppercase",
                  letterSpacing: "0.4px",
                }}
              >
                Name
              </TableCell>


              <TableCell
                align="right"
                sx={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#4b3a58",
                  textTransform: "uppercase",
                  letterSpacing: "0.4px",
                }}
              >
                Action
              </TableCell>

            </TableRow>

          </TableHead>


          <TableBody>

            {members.map((member) => (
              <TableRow
                key={member.employee_id}
                hover
              >

                <TableCell
                  sx={{
                    color: "#51415d",
                    fontSize: "14px",
                    fontWeight: 600,
                  }}
                >
                  {member.display_order}
                </TableCell>


                <TableCell
                  sx={{
                    color: "#4b3a58",
                    fontSize: "14px",
                  }}
                >
                  {member.employee_id}
                </TableCell>


                <TableCell
                  sx={{
                    color: "#2b1748",
                    fontSize: "14px",
                    fontWeight: 600,
                  }}
                >
                  {member.name}
                </TableCell>


                <TableCell align="right">

                  <Button
                    variant="outlined"
                    color="error"
                    size="small"
                    startIcon={
                      <UserX size={16} />
                    }
                    onClick={() =>
                      setMemberToDeactivate(
                        member
                      )
                    }
                    sx={{
                      textTransform: "none",
                      fontWeight: 600,
                      borderRadius: "8px",
                    }}
                  >
                    Deactivate
                  </Button>

                </TableCell>

              </TableRow>
            ))}

          </TableBody>

        </Table>

      </TableContainer>


      {/* ==================================================
          DEACTIVATION CONFIRMATION
          ================================================== */}

      <Dialog
        open={Boolean(memberToDeactivate)}
        onClose={
          handleCancelDeactivate
        }
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: "14px",
            padding: "4px",
          },
        }}
      >

        <DialogTitle>

          <Stack
            direction="row"
            spacing={1.5}
            alignItems="center"
          >

            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 40,
                height: 40,
                borderRadius: "10px",
                background: "#fff7ed",
                color: "#ea580c",
              }}
            >
              <AlertTriangle size={21} />
            </Box>

            <Box>

              <Typography
                variant="h6"
                sx={{
                  fontWeight: 700,
                  color: "#2b1748",
                }}
              >
                Deactivate Employee
              </Typography>

              <Typography
                variant="body2"
                sx={{
                  color: "#75677f",
                  mt: 0.3,
                }}
              >
                This action will deactivate
                the selected employee.
              </Typography>

            </Box>

          </Stack>

        </DialogTitle>


        <DialogContent>

          <Typography
            sx={{
              color: "#51415d",
              fontSize: "14px",
              mb: 2.5,
            }}
          >
            Are you sure you want to
            deactivate this employee?
          </Typography>


          {memberToDeactivate && (
            <Stack spacing={1.2}>

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 14px",
                  borderRadius: "8px",
                  background: "#faf7fd",
                  border: "1px solid #e7ddf0",
                }}
              >

                <Typography
                  variant="caption"
                  sx={{
                    color: "#75677f",
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  Employee ID
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    color: "#2b1748",
                    fontWeight: 600,
                  }}
                >
                  {
                    memberToDeactivate.employee_id
                  }
                </Typography>

              </Box>


              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 14px",
                  borderRadius: "8px",
                  background: "#faf7fd",
                  border: "1px solid #e7ddf0",
                }}
              >

                <Typography
                  variant="caption"
                  sx={{
                    color: "#75677f",
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  Name
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    color: "#2b1748",
                    fontWeight: 600,
                  }}
                >
                  {
                    memberToDeactivate.name
                  }
                </Typography>

              </Box>


              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 14px",
                  borderRadius: "8px",
                  background: "#faf7fd",
                  border: "1px solid #e7ddf0",
                }}
              >

                <Typography
                  variant="caption"
                  sx={{
                    color: "#75677f",
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  Display Order
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    color: "#2b1748",
                    fontWeight: 600,
                  }}
                >
                  {
                    memberToDeactivate.display_order
                  }
                </Typography>

              </Box>

            </Stack>
          )}

        </DialogContent>


        <DialogActions
          sx={{
            padding:
              "12px 24px 20px",
            gap: 1,
          }}
        >

          <Button
            variant="outlined"
            onClick={
              handleCancelDeactivate
            }
            sx={{
              textTransform: "none",
              fontWeight: 600,
              borderRadius: "8px",
              color: "#4b3a58",
              borderColor: "#d8cde5",
            }}
          >
            No
          </Button>


          <Button
            variant="contained"
            color="error"
            startIcon={
              <UserX size={17} />
            }
            onClick={
              handleDeactivate
            }
            sx={{
              textTransform: "none",
              fontWeight: 600,
              borderRadius: "8px",
              boxShadow: "none",
            }}
          >
            I'm Sure
          </Button>

        </DialogActions>

      </Dialog>


      {/* ==================================================
          ADD MEMBER
          ================================================== */}

      <Box
        className="add-member-section"
        sx={{
          mt: 1,
        }}
      >

        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            mb: 2,
          }}
        >

          <UserPlus
            size={19}
            color="#7c3aed"
          />

          <h2 className="subsection-title">
            Add Member
          </h2>

        </Stack>


        <Box
          component="form"
          className="add-member-form"
          onSubmit={
            handleAddMember
          }
        >

          <TextField
            label="Employee ID"
            value={employeeId}
            onChange={(event) =>
              setEmployeeId(
                event.target.value
              )
            }
            required
            fullWidth
            size="small"
          />


          <TextField
            label="Name"
            value={name}
            onChange={(event) =>
              setName(
                event.target.value
              )
            }
            required
            fullWidth
            size="small"
          />


          <Button
            type="submit"
            variant="contained"
            startIcon={
              <Plus size={17} />
            }
            sx={{
              minHeight: "42px",
              textTransform: "none",
              fontWeight: 600,
              borderRadius: "8px",
              boxShadow: "none",
              backgroundColor: "#7c3aed",
              "&:hover": {
                backgroundColor: "#6d28d9",
                boxShadow:
                  "0 3px 8px rgba(124, 58, 237, 0.22)",
              },
            }}
          >
            Add Member
          </Button>

        </Box>

      </Box>

    </section>
  );
}


export default TeamMembers;