OutTextName = "Timestamp Output"

#--------------------------------------#
#--------------CODE BELOW--------------#
#--------------------------------------#

import bpy
from time import sleep

bpy.context.space_data.text.name = "Timestamp Generator"

if OutTextName not in bpy.data.texts:
    bpy.data.texts.new(OutTextName)
OutText = bpy.data.texts[OutTextName]
bpy.context.space_data.text = OutText
#bpy.context.space_data.show_syntax_highlight = False

# This doesn't seem to work
# attempting to move the cursor to the end so it doesn't insert the first line at the beginning
#OutText.current_character = len(OutText.as_string())


curscene = bpy.data.scenes[0]
cursequences = curscene.sequence_editor.sequences

FPS = curscene.render.fps

def find_frame(timestamp_label):
    total_secs = 0
    digits = timestamp_label.split(':')
    i = 0
    while len(digits) > 0:
        total_secs += (60**i)*int(digits.pop())
        i += 1
    frame = FPS * total_secs
    return frame

def find_label(frame):
    total_secs = frame // FPS
    timestamp = "00:00"
    if total_secs > 0:
        mins = int(total_secs // 60)
        secs = int(total_secs % 60)
        timestamp = f"{mins:02}:{secs:02}"
        if total_secs > 60*60:
            hrs = int(total_secs // (60*60))
            timestamp = f"{hrs}:" + timestamp
    return timestamp

def refresh(target_area_type = 'TEXT_EDITOR'):
    for area in bpy.context.screen.areas:
        if area.type == target_area_type:
            area.tag_redraw()

def write_text_with_pause(lines, text_block, pause_duration):
    if lines:
        line = lines.pop(0)
        text_block.write(line)
        #print(f"Added: {line}")

        # Refresh the UI
        refresh()

        # Schedule the next line to be written
        bpy.app.timers.register(lambda: write_text_with_pause(lines, text_block, pause_duration), first_interval=pause_duration)
    else:
        #print("Text generation completed.")
        pass
    return None

AllTimes = []
# Write out the timestamps
for sqc in cursequences:
    if sqc.type != "TEXT": continue
    AllTimes.append((sqc.frame_start,sqc.text))
AllTimes.sort()
lines = ["\nTimestamps\n",] + [find_label(sqcentry[0]) + " " + sqcentry[1] + "\n" for sqcentry in AllTimes]
write_text_with_pause(lines, OutText, 0.001)