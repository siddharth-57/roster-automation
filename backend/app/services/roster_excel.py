import calendar
from datetime import date
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.models.roster_assignment import RosterAssignment
from app.models.team_member import TeamMember


# ------------------------------------------------------
# EXCEL HELPERS
# ------------------------------------------------------

SHIFT_CODES = {"A", "B", "C", "G", "L", "W", "H"}


def get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def get_roster_name(
    year: int,
    month: int,
    group_number: str,
) -> str:
    return (
        f"{year}-{month:02d}-Group-{group_number}"
    )


# ------------------------------------------------------
# LAYOUT
#
#   Rows 1-2             header (dates / weekdays)
#   Rows 3..(2+N)        one row per member
#   blank row
#   9 rows               daily counts (A, B, C, G, W, H, FLEXI, L, TOTAL)
#   1 row                daily working headcount (A+B+C+G)
#   blank row
#   7 rows               legend
#
#   Columns A-C          group / S.No / member name
#   Columns D..          one column per day
#   10 columns           per-member totals
# ------------------------------------------------------

FIRST_MEMBER_ROW = 3
FIRST_DAY_COL = 4  # column D

FONT_NAME = "Arial"

# Per-member totals columns, in order:
# (header text, header fill, formula type, value)
TOTAL_COLUMNS = [
    ('Shift - "A"', "FF66FF", "count", "A"),
    ('Shift - "G"', "83CBEB", "count", "G"),
    ('Shift - "B"', "FFFF00", "count", "B"),
    ('Shift - "C"', "66FF33", "count", "C"),
    ('Comp-Off - "O"', "00B0F0", "count", "O"),
    ("Total - Work", "66FF33", "sum_work", None),
    ('Weekly Off - "W"', "AEAEAE", "count", "W"),
    ('Holiday -"H"', "00B0F0", "count", "H"),
    ('Leave - "L"', "FF0000", "count", "L"),
    ("Total - Days", "66FF33", "sum_days", None),
]

# Daily count rows below the grid:
# (label, fill, font colour, code to count; None = TOTAL row)
SUMMARY_ROWS = [
    ('Shift "A" (6:30 AM to 3:30 PM)', "EC94E2", "000000", "A"),
    ('Shift "B" (2:00 PM to 11:00 PM)', "FFFF00", "000000", "B"),
    ('Shift "C" (10:00 PM to 7:00 AM)', "66FF33", "000000", "C"),
    ('Shift "G" (9:00 AM to 6:00 PM)', "83CBEB", "000000", "G"),
    ("Weekly Off (W & W)", "D9D9D9", "000000", "W"),
    ("Holiday", "FCE4D6", "000000", "H"),
    ("FLEXI", "00B0F0", "FFFFFF", "F"),
    ("Leave", "FF0000", "FFFFFF", "L"),
    ("TOTAL Number of People", "99FFCC", "000000", None),
]

# Legend at the bottom: (label, label fill, label font colour, code)
LEGEND_ROWS = [
    ('Shift "A" (6:30 AM to 3:30 PM)', "EC94E2", "000000", "A"),
    ('Shift "B" (2:00 PM to 11:00 PM)', "FFFF00", "000000", "B"),
    ('Shift "C" (10:00 PM to 7:00 AM)', "66FF33", "000000", "C"),
    ('Shift "G" (9:00 AM to 6:00 PM)', "83CBEB", "000000", "G"),
    ("Weekly Off (W & W)", "D9D9D9", "000000", "W"),
    ("Leave", "FF0000", "FFFFFF", "L"),
    ("Holiday", "FCE4D6", "000000", "H"),
]

# Colour of each shift code inside the roster grid:
# (background, font colour)
SHIFT_COLOURS = {
    "A": ("FF99FF", "000000"),
    "B": ("FFFF00", "000000"),
    "C": ("36EA58", "000000"),
    "G": ("66FFFF", "000000"),
    "W": ("BFBFBF", "000000"),
    "H": ("FCE4D6", "000000"),
    "L": ("FF0000", "FFFFFF"),
    "O": ("00B0F0", "000000"),
}

THIN = Side(style="thin", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")
CENTER_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)
VERTICAL = Alignment(horizontal="center", vertical="center", text_rotation=90)


def fill(hex_colour: str) -> PatternFill:
    return PatternFill(
        fill_type="solid",
        start_color=hex_colour,
        end_color=hex_colour,
    )


def font(
    size: float = 10,
    bold: bool = False,
    colour: str = "000000",
) -> Font:
    return Font(name=FONT_NAME, size=size, bold=bold, color=colour)


def style_cell(
    cell,
    fill_colour: str | None = None,
    cell_font: Font | None = None,
    alignment: Alignment = CENTER,
    border: bool = True,
) -> None:
    if fill_colour:
        cell.fill = fill(fill_colour)
    cell.font = cell_font or font()
    cell.alignment = alignment
    if border:
        cell.border = BORDER


def merge_and_style(
    worksheet: Worksheet,
    first_row: int,
    first_col: int,
    last_row: int,
    last_col: int,
    value,
    **style,
):
    """Write a value, style every cell in the range (so borders show), then merge."""
    cell = worksheet.cell(row=first_row, column=first_col, value=value)

    for row in range(first_row, last_row + 1):
        for col in range(first_col, last_col + 1):
            style_cell(worksheet.cell(row=row, column=col), **style)

    if first_row != last_row or first_col != last_col:
        worksheet.merge_cells(
            start_row=first_row,
            start_column=first_col,
            end_row=last_row,
            end_column=last_col,
        )

    return cell


# ------------------------------------------------------
# BUILD WORKBOOK (pure function: no database access)
# ------------------------------------------------------

def build_roster_workbook(
    year: int,
    month: int,
    group_number: str,
    members: list[tuple[str, str]],
    assignment_lookup: dict[tuple[str, int], str],
) -> Workbook:
    """
    Build the formatted roster workbook.

    members:            [(employee_id, name), ...] in display order
    assignment_lookup:  {(employee_id, day): shift}
    """

    workbook = Workbook()
    ws = workbook.active
    ws.title = "Roster"

    days_in_month = get_days_in_month(year, month)
    member_count = len(members)

    last_member_row = FIRST_MEMBER_ROW + member_count - 1
    last_day_col = FIRST_DAY_COL + days_in_month - 1
    first_total_col = last_day_col + 1
    last_total_col = first_total_col + len(TOTAL_COLUMNS) - 1

    first_day_letter = get_column_letter(FIRST_DAY_COL)
    last_day_letter = get_column_letter(last_day_col)

    # --------------------------------------------------
    # Header: group / S.No / member name (rows 1-2)
    # --------------------------------------------------

    merge_and_style(
        ws, 1, 1, 2, 1, f"Group = {group_number}",
        fill_colour="8ED973", cell_font=font(10, bold=True), alignment=VERTICAL,
    )
    merge_and_style(
        ws, 1, 2, 2, 2, "S.No",
        fill_colour="8ED973", cell_font=font(10, bold=True), alignment=VERTICAL,
    )
    merge_and_style(
        ws, 1, 3, 2, 3, "MOCC Members",
        fill_colour="8ED973", cell_font=font(10, bold=True), alignment=CENTER_WRAP,
    )

    # --------------------------------------------------
    # Header: dates (row 1) and weekdays (row 2)
    # --------------------------------------------------

    for day in range(1, days_in_month + 1):
        col = FIRST_DAY_COL + day - 1
        current = date(year, month, day)
        is_weekend = current.weekday() >= 5

        date_cell = ws.cell(row=1, column=col, value=current)
        date_cell.number_format = "d-mmm"
        style_cell(date_cell, "F6C6AD", font(9, bold=True), VERTICAL)

        weekday_cell = ws.cell(row=2, column=col, value=current.strftime("%a"))
        style_cell(
            weekday_cell,
            "AEAEAE" if is_weekend else "F6C6AD",
            font(9, bold=True),
            VERTICAL,
        )

    # --------------------------------------------------
    # Header: per-member totals columns
    # --------------------------------------------------

    for offset, (title, header_fill, _, _) in enumerate(TOTAL_COLUMNS):
        col = first_total_col + offset
        merge_and_style(
            ws, 1, col, 2, col, title,
            fill_colour=header_fill, cell_font=font(9), alignment=VERTICAL,
        )

    # --------------------------------------------------
    # Member rows
    # --------------------------------------------------

    for index, (employee_id, name) in enumerate(members):
        row = FIRST_MEMBER_ROW + index

        style_cell(ws.cell(row=row, column=1), "66FFFF")
        style_cell(
            ws.cell(row=row, column=2, value=index + 1),
            "66FFFF", font(10, bold=True),
        )
        style_cell(
            ws.cell(row=row, column=3, value=name.strip()),
            "E1E8F0", font(9),
        )

        for day in range(1, days_in_month + 1):
            col = FIRST_DAY_COL + day - 1
            shift = assignment_lookup.get((employee_id, day))
            style_cell(ws.cell(row=row, column=col, value=shift), None, font(11))

        # Per-member totals (live formulas)
        grid = f"{first_day_letter}{row}:{last_day_letter}{row}"
        work_first = get_column_letter(first_total_col)          # A
        work_last = get_column_letter(first_total_col + 4)       # O
        days_first = get_column_letter(first_total_col + 5)      # Total - Work
        days_last = get_column_letter(first_total_col + 8)       # L

        for offset, (_, _, kind, code) in enumerate(TOTAL_COLUMNS):
            col = first_total_col + offset

            if kind == "count":
                formula = f'=COUNTIF({grid},"{code}")'
                cell_fill = "FFF2CC"
            elif kind == "sum_work":
                formula = f"=SUM({work_first}{row}:{work_last}{row})"
                cell_fill = "36EA58"
            else:  # sum_days
                formula = f"=SUM({days_first}{row}:{days_last}{row})"
                cell_fill = "36EA58"

            style_cell(ws.cell(row=row, column=col, value=formula), cell_fill, font(10))

    # --------------------------------------------------
    # Shift colours in the grid (conditional formatting,
    # so colours follow edits made in Excel)
    # --------------------------------------------------

    if member_count:
        grid_range = (
            f"{first_day_letter}{FIRST_MEMBER_ROW}:"
            f"{last_day_letter}{last_member_row}"
        )

        for code, (background, text_colour) in SHIFT_COLOURS.items():
            ws.conditional_formatting.add(
                grid_range,
                CellIsRule(
                    operator="equal",
                    formula=[f'"{code}"'],
                    fill=fill(background),
                    font=Font(color=text_colour),
                ),
            )

    # --------------------------------------------------
    # Daily counts below the grid
    # --------------------------------------------------

    summary_start = last_member_row + 2
    total_row = summary_start + len(SUMMARY_ROWS) - 1

    for offset, (label, row_fill, text_colour, code) in enumerate(SUMMARY_ROWS):
        row = summary_start + offset
        is_total = code is None

        merge_and_style(
            ws, row, 1, row, 3, label,
            fill_colour=row_fill, cell_font=font(9, bold=True, colour=text_colour),
        )

        for day in range(1, days_in_month + 1):
            col = FIRST_DAY_COL + day - 1
            letter = get_column_letter(col)

            if is_total:
                formula = f"=SUM({letter}{summary_start}:{letter}{total_row - 1})"
            else:
                formula = (
                    f'=COUNTIF({letter}{FIRST_MEMBER_ROW}:'
                    f'{letter}{last_member_row},"{code}")'
                )

            style_cell(
                ws.cell(row=row, column=col, value=formula),
                row_fill, font(9, colour=text_colour),
            )

    # Working headcount per day (A + B + C + G), unlabeled as in the original
    working_row = total_row + 1
    for day in range(1, days_in_month + 1):
        col = FIRST_DAY_COL + day - 1
        letter = get_column_letter(col)
        style_cell(
            ws.cell(
                row=working_row,
                column=col,
                value=f"=SUM({letter}{summary_start}:{letter}{summary_start + 3})",
            ),
            None, font(11), border=False,
        )

    # --------------------------------------------------
    # Off-days note (beside the daily counts)
    # --------------------------------------------------

    weekdays = [date(year, month, d).weekday() for d in range(1, days_in_month + 1)]
    saturdays = weekdays.count(5)
    sundays = weekdays.count(6)

    # Holidays aren't stored on the roster, so use the H count
    # (every member gets the same number of H).
    holidays = max(
        (
            sum(
                1
                for day in range(1, days_in_month + 1)
                if assignment_lookup.get((employee_id, day)) == "H"
            )
            for employee_id, _ in members
        ),
        default=0,
    )

    divider = "-" * 38
    note = (
        f"{saturdays}-Saturday\n"
        f"{sundays}-Sunday\n"
        f"{holidays}-Holiday\n"
        f"{divider}\n"
        f"Total ={saturdays + sundays + holidays} Offs\n"
        f"{divider}"
    )

    merge_and_style(
        ws, summary_start, first_total_col + 1, total_row, last_total_col, note,
        fill_colour="FFC000", cell_font=font(9, bold=True), alignment=CENTER_WRAP,
    )

    # --------------------------------------------------
    # Legend
    # --------------------------------------------------

    legend_start = working_row + 2

    for offset, (label, label_fill, text_colour, code) in enumerate(LEGEND_ROWS):
        row = legend_start + offset

        merge_and_style(
            ws, row, 3, row, 6, label,
            fill_colour=label_fill, cell_font=font(9, bold=True, colour=text_colour),
        )

        background, code_colour = SHIFT_COLOURS[code]
        style_cell(
            ws.cell(row=row, column=9, value=code),
            background, font(11, colour=code_colour),
        )

    # --------------------------------------------------
    # Sizes, freeze panes and printing
    # --------------------------------------------------

    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 4.5
    ws.column_dimensions["C"].width = 22

    for col in range(FIRST_DAY_COL, last_day_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 5

    for col in range(first_total_col, last_total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 4.5

    ws.row_dimensions[1].height = 42
    ws.row_dimensions[2].height = 28

    ws.freeze_panes = ws.cell(row=FIRST_MEMBER_ROW, column=FIRST_DAY_COL)

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    return workbook


# ------------------------------------------------------
# EXPORT ROSTER TO EXCEL
# ------------------------------------------------------

def create_roster_excel(
    db: Session,
    roster: Roster,
) -> BytesIO:
    """
    Create the formatted Excel workbook for an existing roster.
    """

    # --------------------------------------------------
    # Get employees who actually have assignments in
    # this roster.
    #
    # We intentionally do NOT filter by active=True.
    # A deactivated employee may still belong to an
    # old/historical roster.
    # --------------------------------------------------

    assignments = db.scalars(
        select(RosterAssignment)
        .where(
            RosterAssignment.roster_id
            == roster.roster_id
        )
    ).all()

    employee_ids = {
        assignment.employee_id
        for assignment in assignments
    }

    # --------------------------------------------------
    # Get those employees from team_members and order
    # them according to their current display_order.
    # --------------------------------------------------

    members = db.scalars(
        select(TeamMember)
        .where(
            TeamMember.employee_id.in_(employee_ids)
        )
        .order_by(TeamMember.display_order)
    ).all()

    assignment_lookup = {
        (assignment.employee_id, assignment.date.day): assignment.shift
        for assignment in assignments
    }

    workbook = build_roster_workbook(
        year=roster.year,
        month=roster.month,
        group_number=roster.group_number,
        members=[
            (member.employee_id, member.name)
            for member in members
        ],
        assignment_lookup=assignment_lookup,
    )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return output


# ------------------------------------------------------
# IMPORT ROSTER FROM EXCEL
# ------------------------------------------------------

def read_roster_excel(
    db: Session,
    file_contents: bytes,
    year: int,
    month: int,
    group_number: str,
) -> dict[str, dict[int, str]]:
    """
    Read a roster Excel file and convert it into the
    internal roster representation:

        {
            "E001": {
                1: "A",
                2: "W",
                ...
            }
        }

    The employee name in the Excel file is matched against
    the team member table.
    """

    members = db.scalars(
        select(TeamMember)
    ).all()

    member_by_name = {
        member.name.strip().lower(): member.employee_id
        for member in members
    }

    return parse_roster_workbook(
        file_contents=file_contents,
        year=year,
        month=month,
        group_number=group_number,
        member_by_name=member_by_name,
    )


def parse_roster_workbook(
    file_contents: bytes,
    year: int,
    month: int,
    group_number: str,
    member_by_name: dict[str, str],
) -> dict[str, dict[int, str]]:
    """
    Pure parsing logic (no database access).

    member_by_name: {lowercased name: employee_id}
    """

    workbook = load_workbook(
        BytesIO(file_contents),
        data_only=True,
    )

    worksheet = workbook.worksheets[0]

    days_in_month = get_days_in_month(
        year,
        month,
    )

    # --------------------------------------------------
    # Validate the group number.
    # --------------------------------------------------

    group_value = worksheet.cell(
        row=1,
        column=1,
    ).value

    expected_group = (
        f"Group = {group_number}"
    )

    if str(group_value).strip() != expected_group:
        raise ValueError(
            f"Excel group does not match "
            f"the selected group number. "
            f"Expected '{expected_group}'."
        )

    roster = {}

    # --------------------------------------------------
    # Read member rows.
    #
    # Members are the continuous block of rows starting
    # at row 3. The first row with an empty name ends the
    # block, so the daily counts and legend below it are
    # never mistaken for members.
    # --------------------------------------------------

    for row in range(
        FIRST_MEMBER_ROW,
        worksheet.max_row + 1,
    ):
        name_value = worksheet.cell(
            row=row,
            column=3,
        ).value

        if name_value is None or str(name_value).strip() == "":
            break

        name = str(name_value).strip()

        employee_id = member_by_name.get(
            name.lower()
        )

        if not employee_id:
            raise ValueError(
                f"Employee '{name}' from the "
                f"Excel file does not exist "
                f"in the team members table."
            )

        roster[employee_id] = {}

        for day in range(
            1,
            days_in_month + 1,
        ):
            column = FIRST_DAY_COL + day - 1

            value = worksheet.cell(
                row=row,
                column=column,
            ).value

            if value is None:
                continue

            shift = str(value).strip().upper()

            if shift == "":
                continue

            if shift not in SHIFT_CODES:
                raise ValueError(
                    f"Invalid shift '{shift}' "
                    f"for employee '{name}' "
                    f"on day {day}."
                )

            roster[employee_id][day] = shift

    return roster