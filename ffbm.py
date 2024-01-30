#!/usr/bin/env python3
import os
import sqlite3
import shutil
import sys
import subprocess

#
# ffbm (Firefox bookmarks) - a script to open a Firefox's bookmark using dmenu.
# It's as basic as it can get, no refunds.
#

# Paths to the target files.
mozilla_folder = os.path.expandvars('$HOME/.mozilla')
db_name = 'places.sqlite'  # Default DB file with Firefox's bookmarks.
tmp_file = f'/tmp/{db_name}'

# Usually first positions are reserved for pre-existing bookmarks,
# e.g: Get Help, Customize Firefox, etc.
default_bookmark_amount = 6
# Separator to use in dmenu. Should be relatively rare.
separator = ' ↦ '

# We'll need to copy the database file in case
# it's locked by an open Firefox instance.
for root, dirs, files in os.walk(mozilla_folder):
    for file in files:
        if file == db_name and root != mozilla_folder:
            path = f'{root}/{file}'
            print(f"Found DB at '{path}'.",
                  file=sys.stderr)
            # Copy the first one, idgaf about multiple profiles.
            shutil.copy(path, tmp_file)
            break

conn = sqlite3.connect(tmp_file)
cur = conn.cursor()

title_to_id = {}
same_titles = {}
longest_title_length = 0

rows = cur.execute('select fk, title from moz_bookmarks')
for (fk, title) in rows.fetchall():
    if fk is None:
        # It's a folder or something.
        continue
    if int(fk) <= default_bookmark_amount:
        # Skip 'Get Help' and all that, I don't need any help.
        continue

    if title in title_to_id.keys():
        # Two bookmarks has the same title.
        if title not in same_titles.keys():
            same_titles[title] = 1
        same_titles[title] += 1
        title += f' [{same_titles[title]}]'

    title_to_id[title] = fk
    # This will not work properly if you have korean/emoji/etc
    # in bookmark titles. I'm not fixing this.
    longest_title_length = max(longest_title_length, len(title))

dmenu_input = ''

for (title, id) in title_to_id.items():
    (url, *_) = cur.execute(f'select url from moz_places where id = {id}')\
        .fetchone()
    dmenu_input += '{:{}s}{}{}\n'.format(title, longest_title_length,
                                         separator, url)

cur.close()

# dmenu is expected to have the xyw patch, customize these params if you want.
dmenu_result = subprocess.run(['dmenu', '-l', '20', '-y', '400', '-i'],
                              stdout=subprocess.PIPE,
                              input=dmenu_input.encode('utf-8'))
dmenu_result = dmenu_result.stdout.decode('utf-8').strip()
if len(dmenu_result) == 0:
    print('Picked nothing.', file=sys.stderr)
    os.unlink(tmp_file)
    exit(1)

choice = dmenu_result.split(separator)[1]
print(f'Picked: {choice}', file=sys.stderr)

# Change the 'xdg-open' to something you use, if on Mac OS, etc.
subprocess.run(['xdg-open', choice], stdout=sys.stderr)

os.unlink(tmp_file)
