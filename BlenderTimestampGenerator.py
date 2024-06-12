
Example_labels_Text = """00:00 Ren Faire
06:59 Summer Game Fest 2022
11:35 Diablo Immortal
19:18 Amazing Cultivation Simulator
22:30 Midnight Fight Express
26:59 Mythic tier
29:47 Homeworld: Deserts of Kharak
39:20 Cyberpunk spire
41:20 Mailbag: Collectibles and Unlockables
52:26 Mailbag: New experience increases appreciation of old thing
1:01:07 Outro"""


import bpy

OutText = bpy.data.texts["Output"]

#--------------------------------------#
#--------------CODE BELOW--------------#
#--------------------------------------#


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
        timestamp = f"{mins}:{secs}"
        if total_secs > 60*60:
            hrs = int(total_secs // (60*60))
            timestamp = f"{hrs}:" + timestamp
    return timestamp

AllTimes = []
# Write out the timestamps
for sqc in cursequences:
    if sqc.type != "TEXT": continue
    AllTimes.append((sqc.frame_start,sqc.text))
AllTimes.sort()
for sqcentry in AllTimes:
    OutText.write(find_label(sqcentry[0]))
    OutText.write(" ")
    OutText.write(sqcentry[1])
    OutText.write("\n")

