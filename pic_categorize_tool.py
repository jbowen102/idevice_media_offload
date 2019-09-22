from os import listdir, mkdir, devnull
from os.path import isdir
from os.path import exists as path_exists
from shutil import copy2 as sh_copy2
from subprocess import Popen, PIPE

from dir_names import BUFFER_ROOT, CAT_DIRS

class CategorizeError(Exception):
    pass

# Phase 3: Display pics one by one and prompt for where to copy each.
# Check for name collisions.

# Will have to be able to create new training vid folders in training-vid structure.
# Have an option to ignore photo (not categorize and copy anywhere).

# Have a way to specify multiple destinations.

# Allow manual path entry (ex. new Photos & Events folder)

def photo_transfer(start_point=""):
    # Print dict of directory mappings
    print("Categorizing images from buffer:\n\t%s" % BUFFER_ROOT)
    print("Target directories available:")
    for key in CAT_DIRS:
        print(("\t%s:\t%s" % (key, CAT_DIRS[key])).expandtabs(2))

    # Create /dev/null object to dump stdout into.
    FNULL = open(devnull, 'w')

    # Initialize manual-sort directory
    mkdir(CAT_DIRS['u'])

    buffered_imgs = listdir(BUFFER_ROOT)
    buffered_imgs.sort()
    if start_point:
        # If a start point is specified, truncate earlier images.
        start_index = buffered_imgs.index(start_point)
        buffered_imgs = buffered_imgs[start_index:]

    for img in buffered_imgs:
        if isdir(img):
            # Ignore any manual sort folder left over from previous offload.
            continue
        img_path = BUFFER_ROOT + img
        # Show image and prompt for location.
        Popen(['xdg-open', img_path], stdout=FNULL, stderr=PIPE)

        target_dir = get_target_dir(img_path)

        if target_dir:
            if img in listdir(target_dir):
                raise CategorizeError("Collision detected: %s in dir:\n\t%s"
                                % (img, target_dir))
            else:
                sh_copy2(img_path, target_dir)
        else:
            # If None was returned by get_target_dir, don't categorize image.
            pass


def get_target_dir(img_path):
    image_name = img_path.split('/')[-1]
    target_input = ""

    while not target_input:
        # Continue prompting until non-empty string input.
        target_input = input("Enter target location for %s (or 'n' for no "
                                            "transfer)\n>" % image_name)

    if target_input == 'st':
        # 'st' type images require target folder creation in most cases.
        return st_target_dir(img_path)
    elif target_input == 'n':
        return None
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
    img_name = img_path.split('/')[-1]
    img_date = img_name.split('T')[0]

    st_root = CAT_DIRS['st']

    if not img_date in listdir(st_root):
        mkdir(st_root + img_date)

    return st_root + img_date



# TEST
photo_transfer()


# reference
# Display image:
# subprocess.Popen('xdg-open', filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
