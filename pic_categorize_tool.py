from os import listdir
from subprocess import Popen

from dir_names import buffer_root



# Phase 3: Display pics one by one and prompt for where to copy each.
# Check for name collisions.

# Will have to be able to create new training vid folders in training-vid structure.
# Have an option to ignore photo (not categorize and copy anywhere).

# Have a way to specify multiple destinations.

# Allow manual path entry (ex. new Photos & Events folder)

for img in listdir(buffer_root):
    img_path =
    subprocess.Popen(['xdg-open', img)




# TEST

# reference
# Display image:
# subprocess.Popen(['xdg-open', [filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
