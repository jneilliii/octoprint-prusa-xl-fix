"""Conservative, lossless insertion for ordinary unframed G-code."""

import re

COMMAND = re.compile(r"^[ \t]*(M106|M107|M201|M203|M221)(?![\d.])", re.IGNORECASE)
PARAMETERS = re.compile(r"(?:[ \t]*[A-Za-z][ \t]*[+-]?(?:\d+(?:\.\d*)?|\.\d+)?)*[ \t]*\Z")


def tool_index(value):
    """Accept XL's zero-based tool slots; reject truncation and booleans."""
    if isinstance(value, bool) or not re.fullmatch(r"[0-4]", str(value)):
        raise ValueError("Tool index must be an integer from 0 to 4")
    return int(value)


def printer_ids(value):
    """Accept a list of printer profile ids. "*" selects every printer."""
    if isinstance(value, str) or not isinstance(value, list):
        raise ValueError("Printers must be a list of printer profile ids")
    ids = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item.strip()
            or any(char in item for char in "/\\\n\r\x00")
        ):
            raise ValueError("Printers must be a list of printer profile ids")
        printer_id = item.strip()
        if printer_id not in ids:
            ids.append(printer_id)
    if "*" in ids:
        return ["*"]
    return ids


def rewrite_command(cmd, tool=0):
    """Return original text unless a target command can safely gain a T word.

    Comments are masked only for inspection. Original bytes are retained.
    Framed, multiline, quoted or malformed input is deliberately untouched.
    """
    tool = tool_index(tool)
    if not isinstance(cmd, str) or "\n" in cmd or "\r" in cmd:
        return cmd
    match = COMMAND.match(cmd)
    if not match:
        return cmd
    visible = []
    depth = 0
    for char in cmd[match.end():]:
        if char == "(" :
            depth += 1
            visible.append(" ")
        elif char == ")":
            if depth == 0:
                return cmd
            depth -= 1
            visible.append(" ")
        elif depth:
            visible.append(" ")
        elif char == ";":
            break
        else:
            visible.append(char)
    if depth:
        return cmd
    parameters = "".join(visible)
    if not PARAMETERS.fullmatch(parameters):
        return cmd
    # Even a bare or malformed T word is explicit: never override it.
    if "T" in parameters.upper():
        return cmd
    suffix = cmd[match.end():]
    separator = "" if not suffix or suffix[0].isspace() else " "
    return cmd[:match.end()] + " T{}".format(tool) + separator + suffix
