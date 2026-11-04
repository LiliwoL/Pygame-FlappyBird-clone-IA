"""Central game configuration and constants."""

# --- Window ---
WIDTH = 420
HEIGHT = 640
FPS = 60
TITLE = "Flappy Bird Clone"

# --- Bird ---
BIRD_X = 110                       # fixed horizontal position of the bird
BIRD_RADIUS = 16                   # collision radius (circle)
GRAVITY = 0.42                     # vertical acceleration per frame
MAX_FALL_SPEED = 11                # terminal falling velocity
FLAP_STRENGTH = -7.5               # impulse applied on flap
FLAP_ROTATE_UP = 25                # max upward tilt (degrees)
FLAP_ROTATE_DOWN = -90             # max downward tilt (degrees)

# --- Pipes ---
PIPE_WIDTH = 70
PIPE_GAP = 150                     # initial vertical gap height
PIPE_MIN_GAP = 108                 # smallest the gap can shrink to
PIPE_SPACING = 230                 # horizontal distance between pipe pairs
PIPE_SPEED = 3.4                   # base scroll speed (px/frame)
PIPE_MARGIN = 60                   # min gap distance from screen top/bottom
PIPE_GAP_SHRINK = 80               # how many points before the gap tightens

# --- Difficulty ramping ---
# As the score grows, speed increases and the gap narrows a little.
SPEED_INCREASE_PER_POINT = 0.025
GAP_SHRINK_PER_POINT = 0.5         # max gap reduction is bounded by PIPE_MIN_GAP

# --- Assets ---
ASSETS_DIR = "assets"
BIRD_SPRITE = "assets/bird.png"
PIPE_SPRITE = "assets/pipe.png"
PIPE_RIM_SPRITE = "assets/pipe_rim.png"
BACKGROUND_SPRITE = "assets/background.png"
GROUND_SPRITE = "assets/ground.png"
CLOUD_SPRITE = "assets/cloud.png"

# --- Colors (fallback palette) ---
SKY_TOP = (111, 197, 232)
SKY_BOTTOM = (238, 248, 240)

COLORS = {
    "bird_body": (255, 222, 89),
    "bird_outline": (222, 150, 36),
    "bird_wing": (255, 200, 60),
    "bird_beak": (255, 140, 50),
    "bird_beak_outline": (200, 90, 20),
    "bird_eye": (255, 255, 255),
    "bird_pupil": (40, 40, 40),
    "pipe": (86, 181, 62),
    "pipe_edge": (122, 201, 67),
    "pipe_dark": (46, 128, 38),
    "pipe_rim": (146, 222, 74),
    "ground_dirt": (222, 205, 160),
    "ground_grass": (116, 204, 84),
    "ground_dark_grass": (62, 168, 66),
}

FLAP_SOUND_FILE = "assets/flap.wav"
POINT_SOUND_FILE = "assets/point.wav"
HIT_SOUND_FILE = "assets/hit.wav"
