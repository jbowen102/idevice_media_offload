from subprocess import Popen



# Phase 3: Display pics one by one and prompt for where to copy each.
# Have a Manual Sort folder to use in case of no correct choice available.
# Prepend date to each file name when copying to various folders.
# Handle name collisions.

# Will have to be able to create new training vid folders in that structure.
# Have an option to ignore photo (not categorize and copy anywhere).

# Have a way to specify multiple destinations.

# Allow manual path entry (ex. new Photos & Events folder)


# reference
# Display image:
# subsystem.Popen(['xdg-open', [filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
