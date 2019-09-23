import pic_offload_tool as offload_tool
import date_organize_tool as org_tool
import pic_categorize_tool as cat_tool


def run_offload():
    print('\t', '*' * 10, 'Offload program', '*' * 10)
    # Instantiate a RawOffloadGroup instance then call its create_new_offload()
    # method.
    rog = offload_tool.RawOffloadGroup()
    rog.create_new_offload()

def run_org():
    print('*' * 10, 'Organize program', '*' * 10)
    # Instantiate an OrganizedGroup instance then call its run_org() method.
    orgg = org_tool.OrganizedGroup()
    orgg.run_org()

def run_cat():
    print('*' * 10, 'Categorize program', '*' * 10)
    # Run photo_transfer()
    cat_tool.photo_transfer()

def run_all():
    print('*' * 10, 'Full offload/organize/categorize program', '*' * 10)
    run_offload()
    run_org()
    run_cat()


# Main loop
while True:
    prog = input("Type 'o' to run the Offload program only.\n"
                 "Type 'g' to run the (date) Organize program only.\n"
                 "Type 'c' to run the Categorize program only.\n"
                 "Type 'a' or press Enter to run all three programs only.\n"
                 "Type 'h' for help.\n>>>")

    if prog.lower() == 'o':
        run_offload()
        break

    elif prog.lower() == 'g':
        run_org()
        break

    elif prog.lower() == 'c':
        run_cat()
        break

    elif not prog.lower() or (prog.lower() == 'a'):
        break

    elif prog.lower() == 'h':
        print('No help available yet.')
        pass

    else:
        print("Invalid response. Try again.")
