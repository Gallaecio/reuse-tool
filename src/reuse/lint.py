# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import contextlib
import json
import os
import sys
from gettext import gettext as _
from typing import Dict

from .project import Project
from .report import ProjectReport


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Prevents output"
    )
    mutex_group = parser.add_mutually_exclusive_group()
    mutex_group.add_argument("-j", "--json", action="store_true", help="Formats output as JSON")
    mutex_group.add_argument("-p", "--plain", action="store_true", help="Formats output as plain text")
    mutex_group.add_argument("--format", nargs="?", choices=("json", "plain"),
                             help="Formats output using the chosen formatter")



# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def format_plain(report: ProjectReport) -> str:
    """Formats data dictionary as plaintext string to be printed to sys.stdout

    :param report: ProjectReport data
    :return: String (in plaintext) that can be output to sys.stdout
    """
    output = ""
    data = report.to_dict()

    # If the project is not compliant:
    if not data["summary"]["compliant"]:

        # Missing copyright and licensing information
        files_without_copyright = set(
            data["non_compliant"]["missing_copyright_info"]
        )
        files_without_license = set(
            data["non_compliant"]["missing_licensing_info"]
        )
        files_without_both = files_without_license.intersection(
            files_without_copyright
        )

        header = (
            "# " + _("MISSING COPYRIGHT AND LICENSING INFORMATION") + "\n\n"
        )
        if files_without_both:
            output += header
            output += _(
                "The following files have no copyright and licensing "
                "information:"
            )
            output += "\n"
            for file in sorted(files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        if files_without_copyright - files_without_both:
            output += header
            output += _("The following files have no copyright information:")
            output += "\n"
            for file in sorted(files_without_copyright - files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        if files_without_license - files_without_both:
            output += header
            output += _("The following files have no licensing information:")
            output += "\n"
            for file in sorted(files_without_license - files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        # Bad licenses
        bad_licenses = data["non_compliant"]["bad_licenses"]
        if bad_licenses:
            output += "# " + _("BAD LICENSES") + "\n\n"
            for lic, files in sorted(bad_licenses.items()):
                output += f"'{lic}' found in:" + "\n"
                for file in sorted(files):
                    output += f"* {file}\n"
            output += "\n\n"

        # Deprecated licenses
        deprecated_licenses = data["non_compliant"]["deprecated_licenses"]
        if deprecated_licenses:
            output += "# " + _("DEPRECATED LICENSES") + "\n\n"
            output += _("The following licenses are deprecated by SPDX:") + "\n"
            for lic in sorted(deprecated_licenses):
                output += f"* {lic}\n"
            output += "\n\n"

        # Licenses without extension
        licenses_without_extension = data["non_compliant"][
            "licenses_without_extension"
        ]
        if licenses_without_extension:
            output += "# " + _("LICENSES WITHOUT FILE EXTENSION") + "\n\n"
            output += _("The following licenses have no file extension:") + "\n"
            for path in sorted(licenses_without_extension):
                output += f"* {str(path)}" + "\n"
            output += "\n\n"

        # Missing licenses
        missing_licenses = data["non_compliant"]["missing_licenses"]
        if missing_licenses:
            output += "# " + _("MISSING LICENSES") + "\n\n"
            for lic, files in sorted(missing_licenses.items()):
                output += f"'{lic}' found in:" + "\n"
                for file in sorted(files):
                    output += f"* {file}\n"
            output += "\n"

        # Unused licenses
        unused_licenses = data["non_compliant"]["unused_licenses"]
        if unused_licenses:
            output += "# " + _("UNUSED LICENSES") + "\n\n"
            output += _("The following licenses are not used:") + "\n"
            for lic in sorted(deprecated_licenses):
                output += f"* {lic}\n"
            output += "\n\n"

        # Read errors
        read_errors = data["non_compliant"]["read_error"]
        if read_errors:
            output += "# " + _("READ ERRORS") + "\n\n"
            output += _("Could not read:") + "\n"
            for path in sorted(read_errors):
                output += f"* {str(path)}" + "\n"
            output += "\n\n"

    output += "# " + _("SUMMARY")
    output += "\n\n"

    summary_contents = [
        (_("Bad licenses:"), ", ".join(data["non_compliant"]["bad_licenses"])),
        (
            _("Deprecated licenses:"),
            ", ".join(data["non_compliant"]["deprecated_licenses"]),
        ),
        (
            _("Licenses without file extension:"),
            ", ".join(
                [
                    file.parts[-1]
                    for file in data["non_compliant"][
                        "licenses_without_extension"
                    ]
                ]
            ),
        ),
        (
            _("Missing licenses:"),
            ", ".join(data["non_compliant"]["missing_licenses"]),
        ),
        (
            _("Unused licenses:"),
            ", ".join(data["non_compliant"]["unused_licenses"]),
        ),
        (_("Used licenses:"), ", ".join(data["summary"]["used_licenses"])),
        (
            _("Read errors: {count}").format(
                count=len(data["non_compliant"]["read_error"])
            ),
            "empty",
        ),
        (
            _("files with copyright information: {count} / {total}").format(
                count=data["summary"]["files_with_copyright_info"],
                total=data["summary"]["files_total"],
            ),
            "empty",
        ),
        (
            _("files with license information: {count} / {total}").format(
                count=data["summary"]["files_with_licensing_info"],
                total=data["summary"]["files_total"],
            ),
            "empty",
        ),
    ]

    for key, value in summary_contents:
        if not value:
            value = "0"
        if value == "empty":
            value = ""
        output += "* " + key + " " + value + "\n"

    if data["summary"]["compliant"]:
        output += _(
            "Congratulations! Your project is compliant with version"
            " {} of the REUSE Specification :-)"
        ).format(data["reuse_version"])
    else:
        output += _(
            "Unfortunately, your project is not compliant with version "
            "{} of the REUSE Specification :-("
        ).format(data["reuse_version"])

    return output


def format_json(report: ProjectReport) -> str:
    """Formats data dictionary as JSON string ready to be printed to sys.stdout

    :param report: Dictionary containing formatted ProjectReport data
    :return: String (representing JSON) that can be output to sys.stdout
    """

    return json.dumps(
        report.to_dict(),
        indent=2,
        # Serialize sets to lists
        default=lambda x: list(x) if isinstance(x, set) else x,
    )


def lint(report: ProjectReport, formatter=format_plain, out=sys.stdout) -> bool:
    """Lints the entire project

    :param report: Dictionary holding formatted ProjectReport data
    :param formatter: Callable that formats the data dictionary
    :param out: Where to output
    """

    out.write(formatter(report))

    data = report.to_dict()
    result = data["summary"]["compliant"]
    return result


def run(args, project: Project, out=sys.stdout, formatter=format_plain):
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    with contextlib.ExitStack() as stack:
        if args.quiet:
            out = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))

        if args.json or args.format == "json":
            formatter = format_json
        elif args.plain or args.format == "plain":
            formatter = format_plain
        else:
            formatter = format_plain

        result = lint(report, formatter=formatter, out=out)

    return 0 if result else 1
