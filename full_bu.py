import pic_offload_tool as offload_tool
import date_organize_tool as org_tool
import pic_categorize_tool as cat_tool

from dir_names import IPHONE_BU_ROOT, IPAD_BU_ROOT


def run_offload(bu_root_dir):
    print('\n\t', '*' * 10, 'OFFLOAD program', '*' * 10)
    # Instantiate a RawOffloadGroup instance then call its create_new_offload()
    # method.
    rog = offload_tool.RawOffloadGroup(bu_root_dir)
    rog.create_new_offload()
    input("\nDuplicate new Raw_Offload data to NAS. "
                "Press Enter when done.")
    print('\t', '*' * 10, 'OFFLOAD program complete', '*' * 10, "\n")
    input("\nYou should proceed to run the ORGANIZE program, even if not "
            "intending to run the CAT program right now.\nThe only reason "
            "not to run ORG after OFFLOAD is if you never intend to CAT this "
            "offload.\n")

def run_org(bu_root_dir, buffer_root_dir):
    print('\n\t', '*' * 10, 'ORGANIZE program', '*' * 10)
    # Instantiate an OrganizedGroup instance then call its run_org() method.
    orgg = org_tool.OrganizedGroup(bu_root_dir, buffer_root_dir)
    orgg.run_org()
    input("\nDuplicate new Organized data to NAS. "
                "Press Enter when done.")
    print('\t', '*' * 10, 'ORGANIZE program complete', '*' * 10, '\n')

def run_cat(buffer_root):
    print('\n\t', '*' * 10, 'CATEGORIZE program', '*' * 10)

    Cat = cat_tool.Categorizer(buffer_root)
    # Prompt user to put all bulk media in appropriate buffers (ex. st_buffer.)
    # Then automatically categorize all.
    Cat.run_auto_cat()
    Cat.photo_transfer()
    input("\nDuplicate new st data to NAS. "
                "Press Enter when done.")
    print('\t', '*' * 10, 'CATEGORIZE program complete', '*' * 10, "\n")

def run_all(bu_root_dir, buffer_root_dir):
    run_offload(bu_root_dir)
    run_org(bu_root_dir, buffer_root_dir)
    run_cat(buffer_root_dir)



device_type = input("Backing up iPhone or iPad? ['o' for iPhone, 'a' for iPad]\n> ")
while device_type not in ['o', 'O', 'a', 'A', 'q', 'Q']:
    device_type = input("Input not recognized. Choose device ['o' for iPhone, "
                                                "'a' for iPad, 'q' to quit]\n> ")
if device_type.lower() == 'o':
    bu_root = IPHONE_BU_ROOT
elif device_type.lower() == 'a':
    bu_root = IPAD_BU_ROOT
elif device_type.lower() == 'q':
    quit()

buffer_root = bu_root + "Cat_Buffer/"

# Main loop
while True:
    prog = input("Choose program to run:\n"
                 "\tType 'f' to run the OFFLOAD program only.\n"
                 "\tType 'g' to run the ORGANIZE (by date) program only.\n"
                 "\tType 'c' to run the CATEGORIZE program only.\n"
                 "\tType 'a' or press Enter to run all three programs.\n"
                 "\tType 'q' to quit.\n"
                 "\tType 'h' for help.\n> ")

    if prog.lower() == 'f':
        run_offload(bu_root)

    elif prog.lower() == 'g':
        run_org(bu_root, buffer_root)

    elif prog.lower() == 'c':
        run_cat(buffer_root)

    elif prog.lower() == 'q':
        break

    elif not prog.lower() or (prog.lower() == 'a'):
        run_all(bu_root, buffer_root)
        break

    elif prog.lower() == 'h':
        print("\tBasic workflow:\n"
            "\t\tRun OFFLOAD and ORGANIZE.\n"
            "\t\tLook at buffer, move all st vids or other big blocks of pics.\n"
            "\t\tRun CAT tool on rest of pics in buffer.\n"
            "\t\tProcess leftover uncategorized pics.\n"
            "\t\tCopy data to NAS.\n")

    else:
        print("Invalid response. Try again.")
