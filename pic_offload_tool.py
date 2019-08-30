# Phase 0: (Manually) Copy folders from phone mapped drive into buffer
# or find where it is mounted.

# Phase 1: Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from buffer all that don’t exist in previous-date folder.
# At end, flush anything left in buffer.

bu_root = input("Confirm BU folder is the following"
                "or input a new directory path:\n"
                "\t/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_pics")
if not bu_root:
    bu_root = ""



# Phase 2: Organize files by date into dated directory.
# Create new folder if none exists

# Phase 3: Display pics one by one and prompt for where to copy each.
# Have a Manual Sort folder to use in case of no correct choice available.
# Prepend date to each file name when copying to various folders.
# Handle name collisions.
