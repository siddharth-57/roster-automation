// Team Members component
// Manages groups and the members in each group.
// UI theme is controlled by App.css and MUI sx props.

import { useEffect, useState } from "react";

import {
  getTeamMembers,
  addTeamMember,
  deactivateTeamMember,
  moveTeamMember,
} from "../services/teamMembers";

import {
  getGroups,
  createGroup,
  renameGroup,
  deactivateGroup,
  activateGroup,
  formatGroupLabel,
  notifyGroupsChanged,
  notifyMembersChanged,
} from "../services/groups";

import {
  AlertTriangle,
  ArrowRightLeft,
  FolderPlus,
  Layers,
  Pencil,
  Plus,
  Power,
  UserPlus,
  UserX,
  Users,
} from "lucide-react";

import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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


// --------------------------------------------------
// SHARED STYLES
// --------------------------------------------------

const headerCellSx = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#4b3a58",
  textTransform: "uppercase",
  letterSpacing: "0.4px",
};

const tableContainerSx = {
  border: "1px solid #e7ddf0",
  borderRadius: "11px",
  overflow: "hidden",
  mb: 4,
};

const primaryButtonSx = {
  minHeight: "40px",
  textTransform: "none",
  fontWeight: 600,
  borderRadius: "8px",
  boxShadow: "none",
  backgroundColor: "#7c3aed",
  "&:hover": {
    backgroundColor: "#6d28d9",
    boxShadow: "0 3px 8px rgba(124, 58, 237, 0.22)",
  },
};

const smallButtonSx = {
  textTransform: "none",
  fontWeight: 600,
  borderRadius: "8px",
};

const dialogPaperProps = {
  sx: {
    borderRadius: "14px",
    padding: "4px",
  },
};


function DetailRow({ label, value }) {
  return (
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
        {label}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: "#2b1748",
          fontWeight: 600,
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}


function TeamMembers() {
  // --------------------------------------------------
  // STATE
  // --------------------------------------------------

  const [groups, setGroups] = useState([]);          // all groups, incl. inactive
  const [members, setMembers] = useState([]);        // all active members

  const [filterGroup, setFilterGroup] = useState(""); // "" = all groups

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Add member
  const [employeeId, setEmployeeId] = useState("");
  const [name, setName] = useState("");
  const [newMemberGroup, setNewMemberGroup] = useState("");

  // Add group
  const [newGroupNumber, setNewGroupNumber] = useState("");
  const [newGroupName, setNewGroupName] = useState("");

  // Dialogs
  const [memberToDeactivate, setMemberToDeactivate] = useState(null);
  const [memberToMove, setMemberToMove] = useState(null);
  const [moveTarget, setMoveTarget] = useState("");
  const [groupToRename, setGroupToRename] = useState(null);
  const [renameValue, setRenameValue] = useState("");


  const activeGroups = groups.filter((group) => group.active);

  const visibleMembers = filterGroup
    ? members.filter((member) => member.group_number === filterGroup)
    : members;


  // --------------------------------------------------
  // LOAD
  // --------------------------------------------------

  const loadAll = async () => {
    try {
      const [groupData, memberData] = await Promise.all([
        getGroups(true),
        getTeamMembers(),
      ]);

      setGroups(groupData);
      setMembers(memberData);

      // Default group for "Add Member": keep the current choice if it's
      // still active, otherwise the first active group.
      const active = groupData.filter((group) => group.active);

      setNewMemberGroup((current) =>
        active.some((group) => group.group_number === current)
          ? current
          : active[0]?.group_number || ""
      );

      setFilterGroup((current) =>
        groupData.some((group) => group.group_number === current)
          ? current
          : ""
      );

    } catch (loadError) {
      setError("Failed to load groups and team members.");
    }
  };


  useEffect(() => {
    loadAll();
  }, []);


  const showError = (requestError, fallback) => {
    setSuccess("");

    const detail = requestError.response?.data?.detail;

    // Most errors arrive as text...
    if (typeof detail === "string") {
      setError(detail);
      return;
    }

    // ...but input validation errors (e.g. a bad group number)
    // arrive as a list from FastAPI.
    if (Array.isArray(detail) && detail.length > 0) {
      setError(
        detail
          .map((item) => String(item.msg || "").replace(/^Value error, /, ""))
          .join(" ")
      );
      return;
    }

    setError(fallback);
  };

  const showSuccess = (message) => {
    setError("");
    setSuccess(message);
  };


  // --------------------------------------------------
  // GROUP ACTIONS
  // --------------------------------------------------

  const handleAddGroup = async (event) => {
    event.preventDefault();

    try {
      const group = await createGroup({
        group_number: newGroupNumber,
        name: newGroupName,
      });

      setNewGroupNumber("");
      setNewGroupName("");

      await loadAll();
      notifyGroupsChanged();

      showSuccess(`Group ${group.group_number} created.`);

    } catch (requestError) {
      showError(requestError, "Failed to create group.");
    }
  };


  const openRename = (group) => {
    setGroupToRename(group);
    setRenameValue(group.name || "");
  };


  const handleRename = async () => {
    if (!groupToRename) {
      return;
    }

    try {
      await renameGroup(groupToRename.group_number, renameValue);

      setGroupToRename(null);

      await loadAll();
      notifyGroupsChanged();

      showSuccess(`Group ${groupToRename.group_number} renamed.`);

    } catch (requestError) {
      showError(requestError, "Failed to rename group.");
    }
  };


  const handleToggleGroup = async (group) => {
    try {
      if (group.active) {
        await deactivateGroup(group.group_number);
      } else {
        await activateGroup(group.group_number);
      }

      await loadAll();
      notifyGroupsChanged();

      showSuccess(
        `Group ${group.group_number} ${group.active ? "deactivated" : "activated"}.`
      );

    } catch (requestError) {
      showError(requestError, "Failed to update group.");
    }
  };


  // --------------------------------------------------
  // MEMBER ACTIONS
  // --------------------------------------------------

  const handleAddMember = async (event) => {
    event.preventDefault();

    try {
      await addTeamMember({
        employee_id: employeeId,
        name: name,
        group_number: newMemberGroup,
      });

      setEmployeeId("");
      setName("");

      await loadAll();
      notifyMembersChanged();
      notifyGroupsChanged(); // member counts changed

      showSuccess(`${name.trim()} added to group ${newMemberGroup}.`);

    } catch (requestError) {
      showError(requestError, "Failed to add team member.");
    }
  };


  const openMove = (member) => {
    setMemberToMove(member);

    const firstOther = activeGroups.find(
      (group) => group.group_number !== member.group_number
    );

    setMoveTarget(firstOther?.group_number || "");
  };


  const handleMove = async () => {
    if (!memberToMove || !moveTarget) {
      return;
    }

    try {
      await moveTeamMember(memberToMove.employee_id, moveTarget);

      const movedName = memberToMove.name;
      setMemberToMove(null);

      await loadAll();
      notifyMembersChanged();
      notifyGroupsChanged();

      showSuccess(`${movedName} moved to group ${moveTarget}.`);

    } catch (requestError) {
      showError(requestError, "Failed to move team member.");
    }
  };


  const handleDeactivate = async () => {
    if (!memberToDeactivate) {
      return;
    }

    try {
      await deactivateTeamMember(memberToDeactivate.employee_id);

      const deactivatedName = memberToDeactivate.name;
      setMemberToDeactivate(null);

      await loadAll();
      notifyMembersChanged();
      notifyGroupsChanged();

      showSuccess(`${deactivatedName} deactivated.`);

    } catch (requestError) {
      showError(requestError, "Failed to deactivate team member.");
    }
  };


  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <section className="app-section">

      {/* ==================================================
          HEADER
          ================================================== */}

      <div className="app-section-header">
        <Stack direction="row" alignItems="center" spacing={1.5}>
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
            <h1>Team Members</h1>
            <p>
              Manage groups, the members in each group, and their
              roster positions.
            </p>
          </Box>
        </Stack>
      </div>


      {/* ==================================================
          MESSAGES
          ================================================== */}

      {error && (
        <Alert
          severity="error"
          icon={<AlertTriangle size={19} />}
          onClose={() => setError("")}
          sx={{ mb: 3, borderRadius: "9px" }}
        >
          {error}
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          onClose={() => setSuccess("")}
          sx={{ mb: 3, borderRadius: "9px" }}
        >
          {success}
        </Alert>
      )}


      {/* ==================================================
          GROUPS
          ================================================== */}

      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <Layers size={19} color="#7c3aed" />
        <h2 className="subsection-title" style={{ margin: 0 }}>
          Groups
        </h2>
      </Stack>

      <TableContainer component={Paper} elevation={0} sx={tableContainerSx}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: "#faf7fd" }}>
              <TableCell sx={headerCellSx}>Group</TableCell>
              <TableCell sx={headerCellSx}>Name</TableCell>
              <TableCell sx={headerCellSx}>Active Members</TableCell>
              <TableCell sx={headerCellSx}>Status</TableCell>
              <TableCell align="right" sx={headerCellSx}>Actions</TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {groups.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ color: "#75677f" }}>
                  No groups yet. Add one below.
                </TableCell>
              </TableRow>
            )}

            {groups.map((group) => (
              <TableRow key={group.group_id} hover>
                <TableCell sx={{ fontWeight: 700, color: "#2b1748" }}>
                  {group.group_number}
                </TableCell>

                <TableCell sx={{ color: "#4b3a58" }}>
                  {group.name || "—"}
                </TableCell>

                <TableCell sx={{ color: "#4b3a58" }}>
                  {group.active_member_count}
                </TableCell>

                <TableCell>
                  <Chip
                    size="small"
                    label={group.active ? "Active" : "Inactive"}
                    color={group.active ? "success" : "default"}
                    variant={group.active ? "filled" : "outlined"}
                  />
                </TableCell>

                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<Pencil size={15} />}
                      onClick={() => openRename(group)}
                      sx={smallButtonSx}
                    >
                      Rename
                    </Button>

                    <Button
                      variant="outlined"
                      size="small"
                      color={group.active ? "error" : "success"}
                      startIcon={<Power size={15} />}
                      onClick={() => handleToggleGroup(group)}
                      sx={smallButtonSx}
                    >
                      {group.active ? "Deactivate" : "Activate"}
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>


      {/* Add group */}

      <Box
        component="form"
        className="add-group-form"
        onSubmit={handleAddGroup}
        sx={{ mb: 5 }}
      >
        <TextField
          label="Group Number"
          placeholder="e.g. 09"
          value={newGroupNumber}
          onChange={(event) =>
            // Digits only, at most 2 ("1" is saved as "01")
            setNewGroupNumber(
              event.target.value.replace(/\D/g, "").slice(0, 2)
            )
          }
          helperText="01 to 99. Can't be changed later."
          inputProps={{ inputMode: "numeric", maxLength: 2 }}
          required
          size="small"
        />

        <TextField
          label="Name (optional)"
          placeholder="e.g. Night Ops"
          value={newGroupName}
          onChange={(event) => setNewGroupName(event.target.value)}
          size="small"
        />

        <Button
          type="submit"
          variant="contained"
          startIcon={<FolderPlus size={17} />}
          sx={primaryButtonSx}
        >
          Add Group
        </Button>
      </Box>


      {/* ==================================================
          MEMBERS
          ================================================== */}

      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "flex-start", sm: "center" }}
        justifyContent="space-between"
        spacing={2}
        sx={{ mb: 2 }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Users size={19} color="#7c3aed" />
          <h2 className="subsection-title" style={{ margin: 0 }}>
            Members
          </h2>
        </Stack>

        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel id="member-filter-label">Show group</InputLabel>
          <Select
            labelId="member-filter-label"
            label="Show group"
            value={filterGroup}
            onChange={(event) => setFilterGroup(event.target.value)}
          >
            <MenuItem value="">All groups</MenuItem>
            {groups.map((group) => (
              <MenuItem key={group.group_id} value={group.group_number}>
                {formatGroupLabel(group)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>

      <TableContainer component={Paper} elevation={0} sx={tableContainerSx}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: "#faf7fd" }}>
              <TableCell sx={headerCellSx}>Group</TableCell>
              <TableCell sx={headerCellSx}>Position</TableCell>
              <TableCell sx={headerCellSx}>Employee ID</TableCell>
              <TableCell sx={headerCellSx}>Name</TableCell>
              <TableCell align="right" sx={headerCellSx}>Actions</TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {visibleMembers.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ color: "#75677f" }}>
                  No active members
                  {filterGroup ? ` in group ${filterGroup}` : ""}.
                </TableCell>
              </TableRow>
            )}

            {visibleMembers.map((member) => (
              <TableRow key={member.employee_id} hover>
                <TableCell sx={{ color: "#51415d", fontWeight: 700 }}>
                  {member.group_number}
                </TableCell>

                <TableCell sx={{ color: "#51415d", fontSize: "14px", fontWeight: 600 }}>
                  {member.display_order}
                </TableCell>

                <TableCell sx={{ color: "#4b3a58", fontSize: "14px" }}>
                  {member.employee_id}
                </TableCell>

                <TableCell sx={{ color: "#2b1748", fontSize: "14px", fontWeight: 600 }}>
                  {member.name}
                </TableCell>

                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<ArrowRightLeft size={15} />}
                      onClick={() => openMove(member)}
                      disabled={activeGroups.length < 2}
                      sx={smallButtonSx}
                    >
                      Move
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      size="small"
                      startIcon={<UserX size={16} />}
                      onClick={() => setMemberToDeactivate(member)}
                      sx={smallButtonSx}
                    >
                      Deactivate
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>


      {/* ==================================================
          ADD MEMBER
          ================================================== */}

      <Box className="add-member-section" sx={{ mt: 1 }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
          <UserPlus size={19} color="#7c3aed" />
          <h2 className="subsection-title">Add Member</h2>
        </Stack>

        <Box
          component="form"
          className="add-member-form with-group"
          onSubmit={handleAddMember}
        >
          <TextField
            label="Employee ID"
            value={employeeId}
            onChange={(event) => setEmployeeId(event.target.value)}
            required
            fullWidth
            size="small"
          />

          <TextField
            label="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            fullWidth
            size="small"
          />

          <FormControl size="small" fullWidth required>
            <InputLabel id="new-member-group-label">Group</InputLabel>
            <Select
              labelId="new-member-group-label"
              label="Group"
              value={newMemberGroup}
              onChange={(event) => setNewMemberGroup(event.target.value)}
            >
              {activeGroups.map((group) => (
                <MenuItem key={group.group_id} value={group.group_number}>
                  {formatGroupLabel(group)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            type="submit"
            variant="contained"
            startIcon={<Plus size={17} />}
            disabled={!newMemberGroup}
            sx={primaryButtonSx}
          >
            Add Member
          </Button>
        </Box>
      </Box>


      {/* ==================================================
          DIALOG: DEACTIVATE MEMBER
          ================================================== */}

      <Dialog
        open={Boolean(memberToDeactivate)}
        onClose={() => setMemberToDeactivate(null)}
        maxWidth="sm"
        fullWidth
        PaperProps={dialogPaperProps}
      >
        <DialogTitle>
          <Stack direction="row" spacing={1.5} alignItems="center">
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
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#2b1748" }}>
                Deactivate Employee
              </Typography>
              <Typography variant="body2" sx={{ color: "#75677f", mt: 0.3 }}>
                This action will deactivate the selected employee.
              </Typography>
            </Box>
          </Stack>
        </DialogTitle>

        <DialogContent>
          <Typography sx={{ color: "#51415d", fontSize: "14px", mb: 2.5 }}>
            Are you sure you want to deactivate this employee?
          </Typography>

          {memberToDeactivate && (
            <Stack spacing={1.2}>
              <DetailRow label="Employee ID" value={memberToDeactivate.employee_id} />
              <DetailRow label="Name" value={memberToDeactivate.name} />
              <DetailRow label="Group" value={memberToDeactivate.group_number} />
              <DetailRow label="Position" value={memberToDeactivate.display_order} />
            </Stack>
          )}
        </DialogContent>

        <DialogActions sx={{ padding: "12px 24px 20px", gap: 1 }}>
          <Button
            variant="outlined"
            onClick={() => setMemberToDeactivate(null)}
            sx={{ ...smallButtonSx, color: "#4b3a58", borderColor: "#d8cde5" }}
          >
            No
          </Button>

          <Button
            variant="contained"
            color="error"
            startIcon={<UserX size={17} />}
            onClick={handleDeactivate}
            sx={{ ...smallButtonSx, boxShadow: "none" }}
          >
            I'm Sure
          </Button>
        </DialogActions>
      </Dialog>


      {/* ==================================================
          DIALOG: MOVE MEMBER
          ================================================== */}

      <Dialog
        open={Boolean(memberToMove)}
        onClose={() => setMemberToMove(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={dialogPaperProps}
      >
        <DialogTitle sx={{ fontWeight: 700, color: "#2b1748" }}>
          Move {memberToMove?.name}
        </DialogTitle>

        <DialogContent>
          <Typography sx={{ color: "#51415d", fontSize: "14px", mb: 2.5 }}>
            Currently in group {memberToMove?.group_number}. They'll be added
            at the end of the new group. Rosters already saved stay under
            the old group.
          </Typography>

          <FormControl size="small" fullWidth>
            <InputLabel id="move-target-label">New group</InputLabel>
            <Select
              labelId="move-target-label"
              label="New group"
              value={moveTarget}
              onChange={(event) => setMoveTarget(event.target.value)}
            >
              {activeGroups
                .filter((group) => group.group_number !== memberToMove?.group_number)
                .map((group) => (
                  <MenuItem key={group.group_id} value={group.group_number}>
                    {formatGroupLabel(group)}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
        </DialogContent>

        <DialogActions sx={{ padding: "12px 24px 20px", gap: 1 }}>
          <Button
            variant="outlined"
            onClick={() => setMemberToMove(null)}
            sx={{ ...smallButtonSx, color: "#4b3a58", borderColor: "#d8cde5" }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            startIcon={<ArrowRightLeft size={16} />}
            onClick={handleMove}
            disabled={!moveTarget}
            sx={primaryButtonSx}
          >
            Move
          </Button>
        </DialogActions>
      </Dialog>


      {/* ==================================================
          DIALOG: RENAME GROUP
          ================================================== */}

      <Dialog
        open={Boolean(groupToRename)}
        onClose={() => setGroupToRename(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={dialogPaperProps}
      >
        <DialogTitle sx={{ fontWeight: 700, color: "#2b1748" }}>
          Rename group {groupToRename?.group_number}
        </DialogTitle>

        <DialogContent>
          <Typography sx={{ color: "#51415d", fontSize: "14px", mb: 2.5 }}>
            Only the display name changes. The group number stays the same,
            so its rosters and Excel files are unaffected. Leave it empty to
            remove the name.
          </Typography>

          <TextField
            label="Name"
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
            fullWidth
            size="small"
            autoFocus
          />
        </DialogContent>

        <DialogActions sx={{ padding: "12px 24px 20px", gap: 1 }}>
          <Button
            variant="outlined"
            onClick={() => setGroupToRename(null)}
            sx={{ ...smallButtonSx, color: "#4b3a58", borderColor: "#d8cde5" }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            startIcon={<Pencil size={16} />}
            onClick={handleRename}
            sx={primaryButtonSx}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

    </section>
  );
}


export default TeamMembers;