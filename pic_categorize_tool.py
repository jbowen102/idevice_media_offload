import os
import shutil
import time
from tqdm import tqdm
import subprocess
import hashlib

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
    if not os.path.exists(st_buffer_path):
        os.mkdir(st_buffer_path)

    # Prompt to move stuff in bulk before looping through img display.
    input("\nDo any mass copies from categorization buffer now (e.g. "
            "into st_buffer) before proceeding."
            "\nPress Enter when ready to continue Cat program.")

    st_buffer_imgs = os.listdir(st_buffer_path)
    if st_buffer_imgs:
        st_buffer_imgs.sort()

        # Loop through st_buffer categorize.
        print("Categorizing st_buffer media now. Progress:")
        for img in tqdm(st_buffer_imgs):
            img_path = st_buffer_path + img
            if os.path.isdir(img_path):
                # Ignore. Shouldn't happen, but handling just in case.
                continue

            target_dir = get_target_dir(img_path, "st")
            if target_dir:
                copy_to_target(img_path, target_dir, move_op=True)
            else:
                # If None returned by get_target_dir, delete image from buffer.
                # This happens for .AAE files.
                os.remove(img_path)

        print("Successfully categorized media from st_buffer.")
    else:
        print("Nothing in st_buffer.")


def photo_transfer(buffer_root, start_point=""):
    """Master function to displays images in buffer and prompt user
    where it should be copied. Execute copy. Start_point can be specified
    (as img name) to skip processing earlier imgs."""

    print("Categorizing images from buffer:\n\t%s\n" % buffer_root)
    # Print dict of directory mappings
    print("Target directories available:")

    # local buffer to be categorized manually
    CAT_DIRS['u'] = buffer_root + "manual_" + time.strftime('%Y-%m-%d') + '/'

    for key in CAT_DIRS:
        print(("\t%s:\t%s" % (key, CAT_DIRS[key])).expandtabs(2))

    print("\n(Append '&' to first choice if multiple destinations needed)\n"
            "(Append '+' followed by a two-digit number to use same dest "
                    "folder for subsequent [number] of pics)\n")

    # Initialize manual-sort directory
    if not os.path.exists(CAT_DIRS['u']):
        os.mkdir(CAT_DIRS['u'])

    buffered_imgs = os.listdir(buffer_root)
    buffered_imgs.sort()
    if start_point:
        # If a start point is specified, truncate earlier images.
        start_index = buffered_imgs.index(start_point)
        buffered_imgs = buffered_imgs[start_index:]

    for img in buffered_imgs:
        img_path = buffer_root + img

        if os.path.isdir(img_path):
            # Ignore any manual sort folder left over from previous offload.
            continue

        # Show image and prompt for location.
        target_dir = get_target_dir(img_path)

        if target_dir and (target_dir[0] == '*'):
            # If get_target_dir detected the trailing special character '&',
            # then after copying image into one place, the user should be
            # prompted again w/ same photo to put somewhere else.
            copy_to_target(img_path, target_dir[1:])
            photo_transfer(buffer_root, img)
            return

        if target_dir and (target_dir[0] == '!'):
            copy_to_target(img_path, target_dir[3:], move_op=True)

            # If get_target_dir detected the trailing special character '+' and
            # a two-digit number, copy multiple successive images to same place.
            additional_copies = int(target_dir[1:3])
            re_buffered_imgs = os.listdir(buffer_root)
            re_buffered_imgs.sort()
            for extra_img in re_buffered_imgs[:additional_copies]:
                extra_img_path = buffer_root + extra_img
                copy_to_target(extra_img_path, target_dir[3:], move_op=True)

            photo_transfer(buffer_root)
            return

        elif target_dir:
            # Execute the move from buffer to appropriate dir. End loop if user
            # returns an abort command due to collision prompt.
            copy_to_target(img_path, target_dir, move_op=True)

        else:
            # If None was returned by get_target_dir, delete image from buffer.
            # This happens with .AAE files.
            os.remove(img_path)

    while os.listdir(CAT_DIRS['u']):
        sort_folder_response = input("\nToday's manual-sort folder populated.\n"
                    "Check folder(s) for any uncategorized pictures and "
                    "categorize them manually.\nPress Enter to continue or 'q' "
                                                                "to quit.\n> ")
        if sort_folder_response.lower() == 'q':
            return
        else:
            continue
    # Once manual sort folder is empty, remove it as long as it's empty.
    if os.path.exists(CAT_DIRS['u']) and not os.listdir(CAT_DIRS['u']):
        os.rmdir(CAT_DIRS['u'])
    # Also remove any other manual sort folders from other days if they're empty.
    for other_folder in os.listdir(buffer_root):
        if "manual_" in other_folder:
            while os.listdir(buffer_root + other_folder):
                other_folder_response = input("\nAt least one manual-sort "
                    "folder in the buffer is populated.\nCategorize content "
                    "then press Enter to continue or 'q' to quit.\n> ")
                if other_folder_response.lower() == 'q':
                    return
                else:
                    continue
            if not os.listdir(buffer_root + other_folder):
                os.rmdir(buffer_root + other_folder)


def get_target_dir(img_path, target_input=""):
    """Function to find and return the directory an image should be copied into
    based on translated user input
    Returns target path."""
    image_name = os.path.basename(img_path)
    # image_name = img_path.split('/')[-1]

    # if image_name[-4:] == ".AAE":
    #     # Don't prompt for AAE files. Just delete.
    #     # They will still exist in raw and organized folders, but it doesn't
    #     # serve any value to copy them elsewhere.
    #     # They can also have dates that don't match the corresponding img/vid.
    #     # This can cause confusion.
    #     return None

    while not target_input:
        # Display pic or video and prompt for dest.
        # Continue prompting until non-empty string input.
        display_photo(img_path)
        target_input = input("Enter target location for %s (or 'n' for no "
                                            "transfer)\n> " % image_name)

    if target_input == 'st':
        # 'st' type images require target folder creation in most cases.
        return st_target_dir(img_path)
    elif target_input == 'n':
        return None
    elif ( (target_input[-1] == '&')
           and (CAT_DIRS.get(target_input[:-1])
                or os.path.isdir(target_input[:-1])) ):
        # If the '&' special character invoked, it means the image needs to be
        # copied into multiple places, and the program should prompt again.
        # pre-pend '*' to returned path to indicate special case to caller.
        return '*' + get_target_dir(img_path, target_input[:-1])
    elif ( len(target_input) >= 3
           and target_input[-3] == '+'
           and (CAT_DIRS.get(target_input[:-3])
                or os.path.isdir(target_input[:-3])) ):
        # If the '+' special character invoked, it means subsequent image(s)
        # need to be copied into same dest.
        # pre-pend '!' to returned path to indicate special case to caller.
        return '!' + target_input[-2:] + get_target_dir(img_path,
                                                            target_input[:-3])
    elif CAT_DIRS.get(target_input):
        return CAT_DIRS[target_input]
    elif os.path.isdir(target_input):
        # Allow manual entry of target path.
        return target_input
    else:
        # Recurse function call until valid input is provided.
        print("Unrecognized input.")
        return get_target_dir(img_path)


def st_target_dir(img_path):
    """Function to find correct directory (or make new) within dated heirarchy
    based on image mod date. Return resulting path."""
    img_name = os.path.basename(img_path)
    # img_name = img_path.split('/')[-1]
    img_date = img_name.split('_')[0]

    st_root = CAT_DIRS['st']

    if not img_date in os.listdir(st_root):
        os.mkdir(st_root + img_date)

    return st_root + img_date


def copy_to_target(img_path, target_dir, new_name=None, move_op=False):
    """Function to copy img to target directory with collision detection.
    If 'move_op' param specified, delete img from current dir."""

    img = os.path.basename(img_path)
    # img = img_path.split('/')[-1]
    if not new_name:
        new_name = img

    # Need to assume trailing slash in target_dir later.
    if target_dir[-1] != "/":
        target_dir += "/"

    # Prompt user for decision if collision detected.
    target_dir_imgs = os.listdir(target_dir)
    if new_name in target_dir_imgs:

        if same_hash(img_path, os.path.join(target_dir, new_name)):
            # First check if they are the same file. If so, don't replace.
            print("%s/%s with same file hash exists already. "
                                    "Dest file not overwritten.\n"
                                % (os.path.basename(target_dir[:-1]), new_name))
            if move_op:
                os.remove(img_path)
            else:
                return

        else:
            # Otherwise, need user input to decide what to do about collision.
            action = None
            while action != "s" and action != "o" and action != "k":
                action = input("Collision detected: %s in dir:\n\t%s\n"
                    "\tSkip, overwrite, or keep both? [S/O/K]\n\t>>> "
                                                % (new_name, target_dir))
                if action.lower() == "s":
                    return
                elif action.lower() == "o":
                    # Overwrite file in destination folder w/ same name.
                    os.remove(os.path.join(target_dir, new_name))
                    shutil.move(img_path, target_dir)
                    return
                elif action.lower() == "k":
                    # repeatedly check for existence of duplicates until a free
                    # name appears. Assume there will never be more than 9.
                    # Prefer shorter file name to spare leading zeros.
                    img_noext = os.path.splitext(new_name)[0]
                    img_ext = os.path.splitext(new_name)[-1]

                    n = 1
                    img_noext = img_noext + "_%d" % n

                    while img_noext + img_ext in target_dir_imgs:
                        n += 1
                        if n > 9:
                            raise Exception("Image incrementer exceeded 9.\n"
                                        "Check dest folder %s" % target_dir)
                        img_noext = img_noext[:-1] + "%d" % n
                    if move_op:
                        shutil.move(img_path,
                                os.path.join(target_dir, img_noext + img_ext))
                    else:
                        shutil.copy2(img_path,
                                os.path.join(target_dir, img_noext + img_ext))

    elif move_op:
        shutil.move(img_path, os.path.join(target_dir, new_name))
    else:
        shutil.copy2(img_path, os.path.join(target_dir, new_name))


def display_photo(img_path):
    # Create /dev/null object to dump stdout into.
    with open(os.devnull, 'w') as FNULL:
        subprocess.run(['xdg-open', img_path],
                                        stdout=FNULL, stderr=subprocess.PIPE)


def same_hash(img1_path, img2_path):
    with open(img1_path, 'rb') as file_obj:
        img1_hash = hashlib.sha1(file_obj.read())
        # print(img1_hash.hexdigest())

    with open(img2_path, 'rb') as file_obj:
        img2_hash = hashlib.sha1(file_obj.read())
        # print(img2_hash.hexdigest())

    if img1_hash.hexdigest() == img2_hash.hexdigest():
        return True
    else:
        return False

# TEST


# reference
# Display image:
# subprocess.Popen('xdg-open', filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
