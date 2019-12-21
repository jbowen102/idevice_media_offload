from os import listdir, mkdir, rmdir, devnull, remove
from os.path import isdir, join
from os.path import exists as path_exists
from os.path import splitext as path_splitext
from os.path import basename as path_basename
from shutil import copy2 as sh_copy2
from shutil import move as sh_move
from time import strftime
from tqdm import tqdm
from subprocess import Popen, PIPE

from dir_names import CAT_DIRS



# Phase 3: Display pics one by one and prompt for where to copy each.
# Have an option to ignore photo (not categorize and copy anywhere).
# Check for name collisions in target directory.
# Allow manual path entry


def auto_cat(buffer_root):
    """Function to automatically categorize st media that user puts in
    st_buffer.
    Later may have other auto categorizing groups, but for now just st."""

    # Initialize st buffer directory to automatically categorize from.
    # Program will automatically categorize by date and move to st root.
    st_buffer_path = buffer_root + "st_buffer/"
    if not path_exists(st_buffer_path):
        mkdir(st_buffer_path)

    # Prompt to move stuff in bulk before looping through img display.
    input("\nCategorization buffer populated. Do any mass copies now (incl. "
            "into st_buffer) before proceeding."
            "\nPress Enter when ready to continue Cat program.")

    st_buffer_imgs = listdir(st_buffer_path)
    if st_buffer_imgs:
        st_buffer_imgs.sort()

        # Loop through st_buffer categorize.
        print("Categorizing st_buffer media now. Progress:")
        for img in tqdm(st_buffer_imgs):
            img_path = st_buffer_path + img
            if isdir(img_path):
                # Ignore. Shouldn't happen, but handling just in case.
                continue

            target_dir = get_target_dir(img_path, "st")
            if target_dir:
                move_to_target(img_path, target_dir)
            else:
                # If None was returned by get_target_dir, delete image from buffer.
                # This happens for .AAE files.
                remove(img_path)

        print("Successfully categorized media from st_buffer.")
    else:
        print("Nothing in st_buffer.")


def photo_transfer(buffer_root, start_point=""):
    """Master function to displays images in buffer and prompt user
    where it should be copied. Execute copy.
    Start_point can be specified (as img name) to skip processing earlier imgs."""

    print("Categorizing images from buffer:\n\t%s" % buffer_root)
    # Print dict of directory mappings
    print("Target directories available (Append '&' to first choice if multiple "
                                                    "destinations needed):")

    # local buffer to be categorized manually
    CAT_DIRS['u'] = buffer_root + "manual_" + strftime('%Y-%m-%d') + '/'

    for key in CAT_DIRS:
        print(("\t%s:\t%s" % (key, CAT_DIRS[key])).expandtabs(2))

    # Initialize manual-sort directory
    if not path_exists(CAT_DIRS['u']):
        mkdir(CAT_DIRS['u'])

    buffered_imgs = listdir(buffer_root)
    buffered_imgs.sort()
    if start_point:
        # If a start point is specified, truncate earlier images.
        start_index = buffered_imgs.index(start_point)
        buffered_imgs = buffered_imgs[start_index:]

    # Create /dev/null object to dump stdout into.
    FNULL = open(devnull, 'w')

    for img in buffered_imgs:
        img_path = buffer_root + img

        if isdir(img_path):
            # Ignore any manual sort folder left over from previous offload.
            continue

        # Show image and prompt for location.
        Popen(['xdg-open', img_path], stdout=FNULL, stderr=PIPE)

        target_dir = get_target_dir(img_path)

        if target_dir and (target_dir[0] == '*'):
            # If get_target_dir detected the trailing special character '&',
            # then after copying image into one place, the user should be
            # prompted again w/ same photo to put somewhere else.
            sh_copy2(img_path, target_dir[1:])
            photo_transfer(buffer_root, img)
            break

        elif target_dir:
            # Execute the move from buffer to appropriate dir. End loop if user
            # returns an abort command due to collision prompt.
            move_to_target(img_path, target_dir)

        else:
            # If None was returned by get_target_dir, delete image from buffer.
            # This happens with .AAE files.
            remove(img_path)

    while listdir(CAT_DIRS['u']):
        input("\nCheck buffer folder for any uncategorized pictures and "
                    "categorize them manually. Press Enter when finished.")
    # Once manual sort folder is empty, remove it. os.rmdir() will error if non-empty.
    rmdir(CAT_DIRS['u'])


def get_target_dir(img_path, target_input=""):
    """Function to find and return the directory an image should be copied into
    based on translated user input
    Returns target path."""
    image_name = path_basename(img_path)
    # image_name = img_path.split('/')[-1]

    if image_name[-4:] == ".AAE":
        # Don't prompt for AAE files. Just delete.
        # They will still exist in raw and organized folders, but it doesn't serve
        # any value to copy them elsewhere.
        # They can also have dates that don't match the corresponding img/vid.
        # This can cause confusion.
        return None

    while not target_input:
        # Continue prompting until non-empty string input.
        target_input = input("Enter target location for %s (or 'n' for no "
                                            "transfer)\n>" % image_name)

    if target_input == 'st':
        # 'st' type images require target folder creation in most cases.
        return st_target_dir(img_path)
    elif target_input == 'n':
        return None
    elif (target_input[-1] == '&') and (CAT_DIRS.get(target_input[:-1])):
        # If the '&' special character invoked, it means the image needs to be
        # copied into multiple places, and the program should prompt another time.
        # pre-pend '*' to returned path to indicate special case to caller.
        return '*' + get_target_dir(img_path, target_input[:-1])
    elif CAT_DIRS.get(target_input):
        return CAT_DIRS[target_input]
    elif path_exists(target_input):
        # Allow manual entry of target path.
        return target_input
    else:
        # Recurse function call until valid input is provided.
        print("Unrecognized input.")
        return get_target_dir(img_path)


def st_target_dir(img_path):
    """Function to find correct directory (or make new) within dated heirarchy
    based on image mod date. Return resulting path."""
    img_name = path_basename(img_path)
    # img_name = img_path.split('/')[-1]
    img_date = img_name.split('_')[0]

    st_root = CAT_DIRS['st']

    if not img_date in listdir(st_root):
        mkdir(st_root + img_date)

    return st_root + img_date


def move_to_target(img_path, target_dir):
    """Function to move img to target directory with collision detection."""

    img = path_basename(img_path)
    # img = img_path.split('/')[-1]

    # Prompt user for decision if collision detected.
    target_dir_imgs = listdir(target_dir)
    if img in target_dir_imgs:
        action = None

        while action != "s" and action != "o" and action != "a":

            action = input("Collision detected: %s in dir:\n\t%s\n"
                "\tSkip, overwrite, or keep both? [S/O/K] >" % (img, target_dir))

            if action.lower() == "s":
                return
            elif action.lower() == "o":
                # Overwrite file in destination folder w/ same name.
                remove(join(target_dir, img))
                sh_move(img_path, target_dir)
                return
            elif action.lower() == "k":
                # repeatedly check for existence of duplicates until a free name appears.
                # assume there will never be more than 9. Prefer shorter file name
                # to spare leading zeros.
                img_noext = path_splitext(img)[0]
                img_ext = path_splitext(img)[-1]

                n = 1
                img_noext = img_noext + "_%d" % n

                while img_noext + img_ext in target_dir_imgs:
                    n += 1
                    img_noext = img_noext[:-1] + "%d" % n

                sh_move(img_path, target_dir + img_noext + img_ext)

    else:
        sh_move(img_path, target_dir)




# TEST


# reference
# Display image:
# subprocess.Popen('xdg-open', filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
