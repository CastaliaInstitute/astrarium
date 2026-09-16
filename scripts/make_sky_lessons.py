import hashlib
import json
import os
import re
import subprocess
import sys

OUT = "/tmp/atlas-content"
VOICES = {"b0": ("en-US-AnaNeural", "-10%"), "b1": ("en-US-AriaNeural", "-15%")}
VOICE_OVERRIDES = {
    "orion-story": ("en-GB-SoniaNeural", "-15%"),
}

LESSONS = [
    ("b1", 1, "Meet Orion the Hunter", "orion",
     "Look up, and find Orion the Hunter. "
     "Three bright stars sit in a neat little row. That is his belt. "
     "Above the belt glows orange Betelgeuse, a giant star that is slowly cooling. "
     "Below shines blue-white Rigel, hot and fierce. "
     "Tomorrow night, Orion will be waiting for you, just a tiny turn further west."),
    ("b1", 1, "Cassiopeia the Queen", "cassiopeia",
     "Find Cassiopeia, the queen on her throne. "
     "She draws a letter W in the sky, made of five bright stars. "
     "Trace the W slowly, from left to right. "
     "The queen sits on the far side of the North Star, opposite the Big Dipper. "
     "All night, she slowly swings around her golden chair."),
    ("b1", 1, "Find the North Star", "north-star",
     "Two stars at the edge of the Big Dipper are called the pointers. "
     "Draw a line through them, upwards, about five times. "
     "There. Polaris, the North Star. "
     "All the other stars wheel around it, all night long, while Polaris stays almost perfectly still. "
     "Sailors found their way home by that quiet, steady star."),
    ("b1", 1, "Counting by Twos", "counting-twos",
     "The stars are playing a counting game tonight. "
     "Two. Four. Six. Eight. Ten. "
     "Now again, a little quieter. "
     "Two. Four. Six. Eight. Ten. "
     "One last time, only in your head."),
    ("b0", 0, "Twinkle, Twinkle, Little Stars", "twinkle",
     "Twinkle, twinkle, little star. How I wonder what you are. "
     "Let us count the brightest ones. One. Two. Three. Four. Five. "
     "Five little stars, blinking goodnight."),
    ("b0", 0, "Goodnight, Sky", "goodnight",
     "The sky is getting sleepy now. Goodnight, stars. Goodnight, moon. "
     "Goodnight, quiet little dove. Close your eyes, little one. "
     "The stars will keep watch until morning."),
    ("b0", 0, "Counting One to Three", "count-one-two-three",
     "Look, little stars. One little star. One. "
     "Two little stars. One, two. Three little stars. One, two, three. "
     "Can you say three? Three!"),
    ("b0", 0, "Star Colors", "star-colors",
     "Stars come in different colors. Some are blue. Some are white. "
     "And some are orange, like warm fire. "
     "Point to a star. What color is it?"),
    ("b1", 1, "The Princess of the Sea", "andromeda",
     "Beside the queen in the sky sits her daughter, the princess Andromeda. "
     "Long ago the princess was left on a rocky shore, waiting for a sea monster that never arrived. "
     "A hero on a winged horse came sweeping out of the sunset, and the monster turned to cold gray stone. "
     "Tonight the princess rests high above you, close to her mother's chair, "
     "two gentle chains of stars beside the Milky Way. "
     "The bravest stories end quietly, and so does this one. Goodnight, princess."),
    ("b0", 0, "Journey to the Stars", "journey-little",
     "We are leaving Earth now, up and up and up. "
     "Look, the Moon is waving goodbye. "
     "Past Mars, the little red planet. "
     "Past Jupiter, big and round. "
     "Past Saturn, wearing its rings. "
     "Now we drift among the stars, quiet and slow. "
     "The stars are our nightlight tonight. Sleep, little traveler."),
    ("b1", 1, "Voyage Through the Universe", "journey-big",
     "Fasten your seatbelt, we are leaving Earth. "
     "The Moon slides past, pale and quiet. "
     "Mars glows red for a moment, then falls behind. "
     "Jupiter fills the window, a giant with a slow, patient storm. "
     "Saturn's rings sweep by like a blade of light. "
     "Now the planets are behind us, and the stars open up around us. "
     "Every star ahead is a sun with its own worlds. "
     "We are drifting now, far and slow, through a neighborhood of suns. "
     "There is nothing to do out here but rest. "
     "Let the stars carry you."),
    ("b0", 0, "The Moon Says Goodnight", "moon-goodnight",
     "The moon is up in the sky. Hello, moon! "
     "The moon is round and bright. It watches little children sleep. "
     "Goodnight, moon. Goodnight, Finn. Goodnight, Aleia. Sleep tight."),
    ("b1", 1, "The Story of Orion and the Scorpion", "orion-story",
     "Long ago, Orion the hunter loved to wander the night forest. "
     "But a giant scorpion guarded the ground, and wherever Orion stepped, the scorpion waited. "
     "The two could never share the same hour. When the hunter rose in the east, the scorpion sank away in the west. "
     "Even now, high above your ceiling, they keep their gentle promise. "
     "Orion sets his bow down just as the scorpion curls up to sleep. "
     "They have circled each other for a thousand years, and never once have met. "
     "Goodnight, Orion. Goodnight, scorpion. Sleep tight, little one."),
    ("b1", 1, "The Queen's Chair", "queens-chair",
     "High above the northern sky sits Cassiopeia, a queen on her golden chair. "
     "Long ago, the queen loved to say she was more beautiful than the sea nymphs. "
     "The sea grew stormy with hurt feelings, and the queen was set in her chair in the stars, "
     "rocking around the North Star, round and round, all night, every night. "
     "She had time to think, up there. And every morning, the sea forgave her. "
     "Tonight she rocks gently, a letter W in the sky, a queen who learned to be quiet."),
    ("b1", 1, "The Great Bear", "great-bear",
     "A long time ago, there was a kind mother who wandered the deep forest. "
     "A jealous king turned her into a great bear, and her little son grew up beside her, "
     "also with fur and paws. "
     "When the king saw how much they loved each other, he softened, and swept them both into the sky "
     "to be safe forever. "
     "Now they walk in circles around the North Star, mother and cub, "
     "never far apart, all night, every night."),
    ("b1", 1, "The Swan's River", "swan-river",
     "Long ago, a swan with silver feathers found the river of stars that runs through the sky. "
     "Every night it flew along the river, carrying wishes in its beak, "
     "from one shore of stars to the other. "
     "The gods were so charmed that they lifted the swan into the sky forever. "
     "Tonight the swan still flies, wings wide, swimming down the Milky Way. "
     "If you whisper a wish at the ceiling, the swan will carry it along the river of stars."),
    ("b1", 1, "The Harp of the Sky", "harp",
     "There was once a musician whose harp could do what no music had ever done. "
     "Trees leaned closer to listen. Rivers slowed down. Even stones grew quiet. "
     "When at last he had to say goodbye to someone he loved, the harp kept playing his song, "
     "soft and low, all by itself. "
     "The gods could not bear to let the music stop, so they hung the harp in the evening sky. "
     "Tonight, Lyra shines above you, its brightest star Vega still humming the first note."),
    ("b1", 1, "The Seven Sisters", "seven-sisters",
     "Seven sisters once lived who loved to dance together, hand in hand, all day long. "
     "When a hunter would not stop following them, they wished on the evening sky, "
     "and the sky lifted them up, past the trees, past the clouds, into the stars. "
     "The hunter still follows, far behind, but he will never catch them. "
     "Look near the shoulder of the Bull: a tiny cluster of stars, close like sisters. "
     "Count them if you can. Some eyes find six. Some find seven."),
    ("b1", 1, "The Winged Horse", "winged-horse",
     "Out of the sea-foam and moonlight, a horse was born with silver wings. "
     "He carried heroes over mountains, and whenever his hooves struck the earth, "
     "a spring of clear water bubbled up. "
     "When his work was done, the gods gave him the whole sky for a pasture. "
     "Tonight the great square of Pegasus stands above you, four stars for a stable door, "
     "and if you watch closely, you might see him paw the sky."),
    ("b0", 0, "The Bear in the Sky", "bear-in-sky",
     "Way up high lives a big bear and a little bear. "
     "They walk around the North Star. Round and round. All night long. "
     "The little bear never lets go of mama's tail. "
     "Round and round. Round and round. All night long."),
    ("b0", 0, "The Queen's Chair", "queens-chair-little",
     "A queen sits in a chair in the sky. "
     "Rocking, rocking, back and forth. "
     "The queen counts the stars. One. Two. Three. "
     "Rocking all night long."),
    ("b0", 0, "The Little Bear", "little-bear",
     "The little bear has a magic star on the end of his tail. "
     "The North Star. It never moves. Never ever. "
     "All the other stars dance around it. "
     "But the North Star stands still, keeping watch. "
     "Goodnight, North Star."),
]


def duration_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return int(float(out))


def build(slug, voice, rate, text):
    text = re.sub(r"\[\[slnc \d+\]\]", " ", text)
    raw = os.path.join(OUT, f"{slug}.mp3")
    final = os.path.join(OUT, f"{slug}.wav")
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice, f"--rate={rate}",
                    "--text", text, "--write-media", raw], check=True, capture_output=True)
    d = duration_of(raw) + 3
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", raw,
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={d}",
        "-f", "lavfi", "-i", f"sine=frequency=164.81:duration={d}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={d}",
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.012:duration={d}",
        "-filter_complex",
        f"[1:a][2:a][3:a][4:a]amix=inputs=4:duration=first:normalize=0,"
        f"lowpass=f=500,volume=0.05[bed];"
        f"[0:a][bed]amix=inputs=2:duration=first:normalize=0,"
        f"afade=t=in:d=2,afade=t=out:st={d - 4}:d=4[a]",
        "-map", "[a]", "-ar", "44100", final,
    ], check=True)
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for key, band, title, slug, text in LESSONS:
        voice, rate = VOICE_OVERRIDES.get(slug, VOICES[key])
        d = build(slug, voice, rate, text)
        manifest.append({
            "id": int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16) % 100000,
            "title": title,
            "band": band,
            "subject": ("math" if slug in ("counting-twos", "count-one-two-three")
                        else "journey" if slug in ("journey-little", "journey-big")
                        else "sky" if slug in ("orion", "cassiopeia", "north-star", "twinkle", "star-colors",
                                               "orion-story", "queens-chair", "great-bear", "swan-river", "harp",
                                               "seven-sisters", "winged-horse", "bear-in-sky", "queens-chair-little",
                                               "little-bear", "andromeda")
                        else "stories"),
            "filePath": f"file:///sdcard/Android/data/institute.castalia.atlas.player/files/lessons/{slug}.wav",
            "durationSec": d,
        })
        print(f"{slug}.wav  {d}s  band {band}  {voice}")
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)


if __name__ == "__main__":
    main()
