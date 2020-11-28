
# Needs to be modified to accept an input path from stdin?

def wpfix(path_in):
    """Function that accepts a Windows path name with backslashes
    and replaces them with forward slashes. Also replaces prefix like C:/ with
    /mnt/c/ for use w/ Windows Subsystem for Linux. Second parameter switches
    this behavior.
    MUST PASS PATH ARGUMENT WITH AN R PREPENDED SO IT'S INTERPRETED AS RAW.
    Example usage:
    datestamp_all(wpfix(r"C:\\my\dir\path"))
    """
    # https://stackoverflow.com/questions/6275695/python-replace-backslashes-to-slashes#6275710

    path_out = path_in.replace("\\", "/")

    drive_letter = path_out[0]
    path_out = path_out.replace("%s:" % drive_letter, "/mnt/%s" % drive_letter.lower())

    # Leaving out tab and newline so output can be redirected in bash scripts
    print("%s" % path_out)
    # print("\t%s\n" % path_out)
    return path_out

