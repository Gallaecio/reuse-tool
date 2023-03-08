# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import contextlib
import os
import sys
from gettext import gettext as _
from textwrap import TextWrapper
from typing import Iterable

from . import __REUSE_version__
from .project import Project
from .report import ProjectReport


def _write_element(element, out=sys.stdout):
    out.write("* ")
    out.write(str(element))
    out.write("\n")


def lint(report: ProjectReport, out=sys.stdout) -> bool:
    """Lint the entire project."""
    bad_licenses_result = lint_bad_licenses(report, out)
    deprecated_result = lint_deprecated_licenses(report, out)
    extensionless = lint_licenses_without_extension(report, out)
    missing_licenses_result = lint_missing_licenses(report, out)
    unused_licenses_result = lint_unused_licenses(report, out)
    read_errors_result = lint_read_errors(report, out)
    files_without_cali = lint_files_without_copyright_and_licensing(report, out)

    lint_summary(report, out=out)

    success = not any(
        any(result)
        for result in (
            bad_licenses_result,
            deprecated_result,
            extensionless,
            missing_licenses_result,
            unused_licenses_result,
            read_errors_result,
            files_without_cali,
        )
    )

    out.write("\n")
    if success:
        out.write(
            _(
                "Congratulations! Your project is compliant with version"
                " {} of the REUSE Specification :-)"
            ).format(__REUSE_version__)
        )
        out.write("\n")
    else:
        out.write(
            _(
                "Unfortunately, your project is not compliant with version "
                "{} of the REUSE Specification :-("
            ).format(__REUSE_version__)
        )
        lint_help(report, out=out)

    return success


def lint_bad_licenses(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for bad licenses. Bad licenses are licenses that are not in the
    SPDX License List or do not start with LicenseRef-.
    """
    bad_files = []

    if report.bad_licenses:
        out.write("# ")
        out.write(_("BAD LICENSES"))
        out.write("\n")
        for lic, files in sorted(report.bad_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_deprecated_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for deprecated licenses."""
    deprecated = []

    if report.deprecated_licenses:
        out.write("# ")
        out.write(_("DEPRECATED LICENSES"))
        out.write("\n\n")
        out.write(_("The following licenses are deprecated by SPDX:"))
        out.write("\n")
        for lic in sorted(report.deprecated_licenses):
            deprecated.append(lic)
            _write_element(lic, out=out)
        out.write("\n\n")

    return deprecated


def lint_licenses_without_extension(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for licenses without extensions."""
    extensionless = []

    if report.licenses_without_extension:
        out.write("# ")
        out.write(_("LICENSES WITHOUT FILE EXTENSION"))
        out.write("\n\n")
        out.write(_("The following licenses have no file extension:"))
        out.write("\n")
        for __, path in sorted(report.licenses_without_extension.items()):
            extensionless.append(path)
            _write_element(path, out=out)
        out.write("\n\n")

    return extensionless


def lint_missing_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for missing licenses. A license is missing when it is referenced
    in a file, but cannot be found.
    """
    bad_files = []

    if report.missing_licenses:
        out.write("# ")
        out.write(_("MISSING LICENSES"))
        out.write("\n")

        for lic, files in sorted(report.missing_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_unused_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for unused licenses."""
    unused_licenses = []

    if report.unused_licenses:
        out.write("# ")
        out.write(_("UNUSED LICENSES"))
        out.write("\n\n")
        out.write(_("The following licenses are not used:"))
        out.write("\n")
        for lic in sorted(report.unused_licenses):
            unused_licenses.append(lic)
            _write_element(lic, out=out)
        out.write("\n\n")

    return unused_licenses


def lint_read_errors(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for read errors."""
    bad_files = []

    if report.read_errors:
        out.write("# ")
        out.write(_("READ ERRORS"))
        out.write("\n\n")
        out.write(_("Could not read:"))
        out.write("\n")
        for file_ in report.read_errors:
            bad_files.append(file_)
            _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_files_without_copyright_and_licensing(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for files that do not have copyright or licensing information."""
    # TODO: The below three operations can probably be optimised.
    both = set(report.files_without_copyright) & set(
        report.files_without_licenses
    )
    only_copyright = set(report.files_without_copyright) - both
    only_licensing = set(report.files_without_licenses) - both

    if any((both, only_copyright, only_licensing)):
        out.write("# ")
        out.write(_("MISSING COPYRIGHT AND LICENSING INFORMATION"))
        out.write("\n\n")
        if both:
            out.write(
                _(
                    "The following files have no copyright and licensing "
                    "information:"
                )
            )
            out.write("\n")
            for file_ in sorted(both):
                _write_element(file_, out=out)
            out.write("\n")
        if only_copyright:
            out.write(_("The following files have no copyright information:"))
            out.write("\n")
            for file_ in sorted(only_copyright):
                _write_element(file_, out=out)
            out.write("\n")
        if only_licensing:
            out.write(_("The following files have no licensing information:"))
            out.write("\n")
            for file_ in sorted(only_licensing):
                _write_element(file_, out=out)
            out.write("\n")
        out.write("\n")

    return both | only_copyright | only_licensing


def lint_summary(report: ProjectReport, out=sys.stdout) -> None:
    """Print a summary for linting."""
    # pylint: disable=too-many-statements
    out.write("# ")
    out.write(_("SUMMARY"))
    out.write("\n\n")

    file_total = len(report.file_reports)

    out.write("* ")
    out.write(_("Bad licenses:"))
    for i, lic in enumerate(sorted(report.bad_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Deprecated licenses:"))
    for i, lic in enumerate(sorted(report.deprecated_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Licenses without file extension:"))
    for i, lic in enumerate(sorted(report.licenses_without_extension)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Missing licenses:"))
    for i, lic in enumerate(sorted(report.missing_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Unused licenses:"))
    for i, lic in enumerate(sorted(report.unused_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Used licenses:"))
    for i, lic in enumerate(sorted(report.used_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Read errors: {count}").format(count=len(report.read_errors)))
    out.write("\n")

    out.write("* ")
    out.write(
        _("Files with copyright information: {count} / {total}").format(
            count=file_total - len(report.files_without_copyright),
            total=file_total,
        )
    )
    out.write("\n")

    out.write("* ")
    out.write(
        _("Files with license information: {count} / {total}").format(
            count=file_total - len(report.files_without_licenses),
            total=file_total,
        )
    )
    out.write("\n")


def lint_help(report: ProjectReport, out=sys.stdout) -> None:
    """Return help for next steps based on found REUSE issues"""
    help_texts = []

    out.write("\n\n\n# ")
    out.write(_("RECOMMENDATIONS"))
    out.write("\n\n")

    # Bad licenses
    if report.bad_licenses:
        help_texts.append(
            _(
                "Fix bad licenses: At least one license in the LICENSES"
                " directory and/or provided by 'SPDX-License-Identifier' tags"
                " is invalid. They are either not valid SPDX license"
                " identifiers or do not start with 'LicenseRef-'. FAQ about"
                " custom licenses: https://reuse.software/faq/#custom-license"
            )
        )

    # Deprecated licenses
    if report.deprecated_licenses:
        help_texts.append(
            _(
                "Fix deprecated licenses: At least one of the licenses in the"
                " LICENSES directory and/or provided by an"
                " 'SPDX-License-Identifier' tag or in '.reuse/dep5' has been"
                " deprecated by SPDX. The current list and their respective"
                " recommended  new identifiers can be found here:"
                " https://spdx.org/licenses/#deprecated"
            )
        )

    # Licenses without file extension
    if report.licenses_without_extension:
        help_texts.append(
            _(
                "Fix licenses without file extension: At least one license text"
                " file in the 'LICENSES' directory does not have a '.txt' file"
                " extension. Please rename the file(s) accordingly."
            )
        )

    # Missing licenses
    if report.missing_licenses:
        help_texts.append(
            _(
                "Fix missing licenses: For at least one of the license"
                " identifiers provided by the 'SPDX-LicenseIdentifier' tags,"
                " there is no corresponding license text file in the 'LICENSES'"
                " directory. For SPDX license identifiers, you can simply run"
                " 'reuse download --all' to get any missing ones. For custom"
                " licenses (starting with 'LicenseRef-'), you need to add these"
                " files yourself."
            )
        )

    # Unused licenses
    if report.unused_licenses:
        help_texts.append(
            _(
                "Fix unused licenses: At least one of the license text files in"
                " 'LICENSES' is not referenced for any file, e.g. by an"
                " 'SPDX-License-Identifier' tag. Please make sure that you"
                " either tag the accordingly licensed files properly, or delete"
                " the unused license text if you are sure that no file or code"
                " snippet is licensed as such."
            )
        )

    # Read errors
    if report.read_errors:
        help_texts.append(
            _(
                "Fix read errors: At least one of the files in your directory"
                " cannot be read by the tool. Please check the file"
                " permissions. You will find the affected files at the top of"
                " the output as part of the logged error messages."
            )
        )

    # Files without copyright and/or licensing information
    if report.files_without_copyright or report.files_without_licenses:
        help_texts.append(
            _(
                "Fix missing copyright/license information: For one or more"
                " files, the tool cannot find copyright and/or license"
                " information. Please add it as a comment in the file header,"
                " ideally using the 'SPDX-FileCopyrightText' tag. If that's not"
                " possible, you can use adjacent '.license' files or the"
                " '.reuse/dep5' file."
            )
        )

    # Output help texts in a nicely wrapped format
    wrapper = TextWrapper(
        width=80,
        drop_whitespace=True,
        break_long_words=False,
        initial_indent="* ",
        subsequent_indent="  ",
    )

    for help_text in help_texts:
        out.write("\n".join(wrapper.wrap(help_text)))
        out.write("\n")


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument(
        "-q", "--quiet", action="store_true", help=_("prevents output")
    )


def run(args, project: Project, out=sys.stdout):
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    with contextlib.ExitStack() as stack:
        if args.quiet:
            out = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
        result = lint(report, out=out)

    return 0 if result else 1
