import bpy
from time import sleep

OutTextName = "Timestamp Output"

bpy.context.space_data.text.name = "Timestamp Generator"

if OutTextName not in bpy.data.texts:
    bpy.data.texts.new(OutTextName)
OutText = bpy.data.texts[OutTextName]
bpy.context.space_data.text = OutText
# bpy.context.space_data.show_syntax_highlight = False

curscene = bpy.data.scenes[0]
cursequences = curscene.sequence_editor.sequences
FPS = curscene.render.fps

def find_frame(timestamp_label):
    """
    Convert a timestamp label (HH:MM:SS) into a frame number.
    
    Args:
        timestamp_label (str): The timestamp label to convert.
    
    Returns:
        int: The frame number corresponding to the given timestamp.
    """
    total_secs = 0
    digits = timestamp_label.split(':')
    i = 0
    while len(digits) > 0:
        total_secs += (60 ** i) * int(digits.pop())
        i += 1
    frame = FPS * total_secs
    return frame

def find_label(frame):
    """
    Convert a frame number into a timestamp label (HH:MM:SS).
    
    Args:
        frame (int): The frame number to convert.
    
    Returns:
        str: The timestamp label corresponding to the given frame.
    """
    total_secs = frame // FPS
    timestamp = "00:00"
    if total_secs > 0:
        mins = int(total_secs // 60)
        secs = int(total_secs % 60)
        timestamp = f"{mins:02}:{secs:02}"
        if total_secs > 60 * 60:
            hrs = int(total_secs // (60 * 60))
            timestamp = f"{hrs}:{timestamp}"
    return timestamp

def refresh(target_area_type='TEXT_EDITOR'):
    """
    Refresh the Blender UI for the specified area type.
    
    Args:
        target_area_type (str): The type of area to refresh (default is 'TEXT_EDITOR').
    """
    for area in bpy.context.screen.areas:
        if area.type == target_area_type:
            area.tag_redraw()

def write_text_with_pause(lines, text_block, pause_duration):
    """
    Write lines of text to a text block with a pause between each line.
    
    Args:
        lines (list): List of lines to write.
        text_block (bpy.types.Text): The text block to write to.
        pause_duration (float): The duration to pause between writing each line.
    """
    if lines:
        line = lines.pop(0)
        text_block.write(line)
        # Refresh the UI
        refresh()

        # Schedule the next line to be written
        bpy.app.timers.register(lambda: write_text_with_pause(lines, text_block, pause_duration), first_interval=pause_duration)
    else:
        # Text generation completed.
        pass
    return None

def generate_timestamps():
    """
    Generate timestamps for all text sequences in the current scene and write them to the output text block.
    """
    AllTimes = []
    # Write out the timestamps
    for sqc in cursequences:
        if sqc.type != "TEXT":
            continue
        AllTimes.append((sqc.frame_start, sqc.text))
    AllTimes.sort()
    lines = ["\nTimestamps\n", ] + [find_label(sqcentry[0]) + " " + sqcentry[1] + "\n" for sqcentry in AllTimes]
    write_text_with_pause(lines, OutText, 0.1)

if __name__ == "__main__":
    generate_timestamps()
