import pic_offload_tool as offload_tool
import date_organize_tool as org_tool
import pic_categorize_tool as cat_tool

from dir_names import DEFAULT_BU_ROOT

def run_offload():
    print('\n\t', '*' * 10, 'OFFLOAD program', '*' * 10)
    # Instantiate a RawOffloadGroup instance then call its create_new_offload()
    # method.
    rog = offload_tool.RawOffloadGroup()
    rog.create_new_offload()
    print('\t', '*' * 10, 'OFFLOAD program complete', '*' * 10, "\n")

def run_org():
    print('\n\t', '*' * 10, 'ORGANIZE program', '*' * 10)
    # Instantiate an OrganizedGroup instance then call its run_org() method.
    orgg = org_tool.OrganizedGroup(DEFAULT_BU_ROOT)
    orgg.run_org()
    print('\t', '*' * 10, 'ORGANIZE program complete', '*' * 10, '\n')

def run_cat():
    print('\n\t', '*' * 10, 'CATEGORIZE program', '*' * 10)
    # Run photo_transfer()
    cat_tool.photo_transfer()
    print('\t', '*' * 10, 'CATEGORIZE program complete', '*' * 10, "\n")

def run_all():
    # print('\n\t', '*' * 10, 'Full offload/organize/categorize program', '*' * 10)
    run_offload()
    run_org()
    run_cat()


# Main loop
while True:
    prog = input("Choose program to run:\n"
                 "\tType 'f' to run the OFFLOAD program only.\n"
                 "\tType 'g' to run the ORGANIZE (by date) program only.\n"
                 "\tType 'c' to run the CATEGORIZE program only.\n"
                 "\tType 'a' or press Enter to run all three programs.\n"
                 "\tType 'q' to quit.\n"
                 "\tType 'h' for help.\n>")

    if prog.lower() == 'f':
        run_offload()

    elif prog.lower() == 'g':
        run_org()

    elif prog.lower() == 'c':
        run_cat()

    elif prog.lower() == 'q':
        break

    elif not prog.lower() or (prog.lower() == 'a'):
        run_all()
        break

    elif prog.lower() == 'h':
        print('No help available yet.')
        pass

    else:
        print("Invalid response. Try again.")
