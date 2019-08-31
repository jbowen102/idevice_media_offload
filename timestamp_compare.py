# requires modification to work. Used in main script then dumped here to get
# out of the way.


# # Compare creation and modification times
# iPhone_root = iPhoneDCIM()
#
# all_APPLE_folders = iPhone_root.get_APPLE_folders()
#
# for APPLE_folder in all_APPLE_folders:
#     APPLE_folder_path = iPhone_root.get_root() + APPLE_folder + '/'
#
#     for img in listdir(APPLE_folder_path):
#         full_img_path = APPLE_folder_path + img
#         ctime_str = strftime('%Y-%m-%d T %H:%M:%S', localtime(getctime(full_img_path)))
#         mtime_str = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(full_img_path)))
#         # print("%s created: %s; modified: %s" % (img, ctime_str, mtime_str))
#         if ctime_str != mtime_str:
#             print("%s created/modified:\n\t%s\n\t%s" % (APPLE_folder +'/'+ img,
#                                                         ctime_str, mtime_str))
#             print("\t\t\t\t^----ctime/mtime discrepancy")
